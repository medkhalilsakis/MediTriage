from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from authentication.models import CustomUser

from .models import Conversation, DirectMessage, UserPresence
from .serializers import ConversationOpenSerializer, DirectMessageCreateSerializer, PresenceHeartbeatSerializer

ONLINE_WINDOW_SECONDS = 75


class MessagingContactsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        allowed_ids = _allowed_contact_user_ids(request.user)
        allowed_ids.discard(request.user.id)

        contacts_qs = CustomUser.objects.filter(id__in=allowed_ids, is_active=True).order_by('role', 'email')
        contacts = list(contacts_qs)

        unread_by_sender = {
            item['sender_id']: item['count']
            for item in DirectMessage.objects.filter(
                recipient=request.user,
                is_read=False,
                sender_id__in=allowed_ids,
            )
            .values('sender_id')
            .annotate(count=Count('id'))
        }

        presence_map = _presence_map_for_user_ids([contact.id for contact in contacts])
        payload = []
        connected_now = 0
        for contact in contacts:
            serialized = _serialize_user(contact, request=request, presence_map=presence_map)
            serialized['unread_count'] = unread_by_sender.get(contact.id, 0)
            payload.append(serialized)
            if serialized['is_online']:
                connected_now += 1

        return Response(
            {
                'results': payload,
                'connected_now': connected_now,
                'total_contacts': len(payload),
            },
            status=status.HTTP_200_OK,
        )


class MessagingConversationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversations = list(_conversations_queryset_for_user(request.user))
        conversation_ids = [conversation.id for conversation in conversations]

        unread_by_conversation = {
            item['conversation_id']: item['count']
            for item in DirectMessage.objects.filter(
                conversation_id__in=conversation_ids,
                recipient=request.user,
                is_read=False,
            )
            .values('conversation_id')
            .annotate(count=Count('id'))
        }

        partner_ids = [
            _other_participant_id(conversation, request.user.id)
            for conversation in conversations
        ]
        presence_map = _presence_map_for_user_ids(partner_ids)

        results = [
            _serialize_conversation_summary(
                conversation=conversation,
                current_user=request.user,
                request=request,
                presence_map=presence_map,
                unread_count=unread_by_conversation.get(conversation.id, 0),
            )
            for conversation in conversations
        ]

        return Response({'results': results}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ConversationOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_id = serializer.validated_data['recipient_id']
        if recipient_id == request.user.id:
            raise ValidationError({'recipient_id': 'You cannot open a conversation with yourself.'})

        try:
            recipient = CustomUser.objects.get(pk=recipient_id)
        except CustomUser.DoesNotExist as exc:
            raise ValidationError({'recipient_id': 'Recipient does not exist.'}) from exc

        _ensure_can_contact(request.user, recipient)

        low_id, high_id = _normalize_participant_ids(request.user.id, recipient.id)
        with transaction.atomic():
            conversation, created = Conversation.objects.get_or_create(
                participant_low_id=low_id,
                participant_high_id=high_id,
                defaults={'created_by': request.user},
            )

        other_user = _get_other_participant(conversation, request.user)
        presence_map = _presence_map_for_user_ids([other_user.id])

        return Response(
            {
                'created': created,
                'conversation': _serialize_conversation_summary(
                    conversation=conversation,
                    current_user=request.user,
                    request=request,
                    presence_map=presence_map,
                    unread_count=0,
                ),
                'other_user': _serialize_user(other_user, request=request, presence_map=presence_map),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MessagingConversationMessagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = _get_conversation_for_user(conversation_id, request.user)

        DirectMessage.objects.filter(
            conversation=conversation,
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)

        limit = min(max(int(request.query_params.get('limit', 120)), 1), 300)
        messages = list(
            DirectMessage.objects.select_related('sender', 'recipient')
            .filter(conversation=conversation)
            .order_by('-created_at')[:limit]
        )
        messages.reverse()

        other_user = _get_other_participant(conversation, request.user)
        presence_map = _presence_map_for_user_ids([other_user.id])

        return Response(
            {
                'conversation': _serialize_conversation_summary(
                    conversation=conversation,
                    current_user=request.user,
                    request=request,
                    presence_map=presence_map,
                    unread_count=0,
                ),
                'other_user': _serialize_user(other_user, request=request, presence_map=presence_map),
                'messages': [
                    {
                        'id': message.id,
                        'conversation': message.conversation_id,
                        'sender_id': message.sender_id,
                        'sender_email': message.sender.email,
                        'recipient_id': message.recipient_id,
                        'recipient_email': message.recipient.email,
                        'content': message.content,
                        'is_read': message.is_read,
                        'created_at': message.created_at,
                    }
                    for message in messages
                ],
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, conversation_id):
        conversation = _get_conversation_for_user(conversation_id, request.user)
        serializer = DirectMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        other_user = _get_other_participant(conversation, request.user)
        if other_user.id == request.user.id:
            raise ValidationError({'detail': 'Invalid conversation participants.'})

        with transaction.atomic():
            message = DirectMessage.objects.create(
                conversation=conversation,
                sender=request.user,
                recipient=other_user,
                content=serializer.validated_data['content'],
            )
            conversation.touch_last_message()

        return Response(
            {
                'id': message.id,
                'conversation': message.conversation_id,
                'sender_id': message.sender_id,
                'sender_email': message.sender.email,
                'recipient_id': message.recipient_id,
                'recipient_email': message.recipient.email,
                'content': message.content,
                'is_read': message.is_read,
                'created_at': message.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class MessagingPresenceHeartbeatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PresenceHeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_online = serializer.validated_data.get('is_online', True)

        presence, _ = UserPresence.objects.get_or_create(user=request.user)
        presence.is_online = is_online
        presence.last_seen = timezone.now()
        presence.save(update_fields=['is_online', 'last_seen', 'updated_at'])

        return Response(
            {
                'is_online': _presence_is_online(presence),
                'last_seen': presence.last_seen,
            },
            status=status.HTTP_200_OK,
        )


class MessagingSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversations_count = _conversations_queryset_for_user(request.user).count()
        unread_count = DirectMessage.objects.filter(recipient=request.user, is_read=False).count()

        allowed_ids = _allowed_contact_user_ids(request.user)
        allowed_ids.discard(request.user.id)
        presence_map = _presence_map_for_user_ids(list(allowed_ids))
        online_contacts = sum(1 for presence in presence_map.values() if _presence_is_online(presence))

        return Response(
            {
                'active_conversations': conversations_count,
                'unread_messages': unread_count,
                'online_contacts': online_contacts,
                'total_contacts': len(allowed_ids),
            },
            status=status.HTTP_200_OK,
        )


def _normalize_participant_ids(user_a_id, user_b_id):
    return tuple(sorted([int(user_a_id), int(user_b_id)]))


def _conversations_queryset_for_user(user):
    return Conversation.objects.select_related('participant_low', 'participant_high').filter(
        Q(participant_low=user) | Q(participant_high=user)
    )


def _get_conversation_for_user(conversation_id, user):
    try:
        conversation = _conversations_queryset_for_user(user).get(pk=conversation_id)
    except Conversation.DoesNotExist as exc:
        raise PermissionDenied('You do not have access to this conversation.') from exc
    return conversation


def _other_participant_id(conversation, current_user_id):
    if conversation.participant_low_id == current_user_id:
        return conversation.participant_high_id
    return conversation.participant_low_id


def _get_other_participant(conversation, current_user):
    if conversation.participant_low_id == current_user.id:
        return conversation.participant_high
    return conversation.participant_low


def _presence_map_for_user_ids(user_ids):
    if not user_ids:
        return {}
    return {
        presence.user_id: presence
        for presence in UserPresence.objects.filter(user_id__in=user_ids)
    }


def _presence_is_online(presence):
    if not presence or not presence.is_online or not presence.last_seen:
        return False
    return (timezone.now() - presence.last_seen) <= timedelta(seconds=ONLINE_WINDOW_SECONDS)


def _serialize_user(user, request, presence_map):
    presence = presence_map.get(user.id)
    profile_image_url = ''
    if getattr(user, 'profile_image', None):
        profile_image_url = user.profile_image.url
        if request is not None:
            profile_image_url = request.build_absolute_uri(profile_image_url)

    full_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
    return {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'full_name': full_name or user.email,
        'profile_image_url': profile_image_url,
        'is_online': _presence_is_online(presence),
        'last_seen': presence.last_seen if presence else None,
    }


def _serialize_conversation_summary(conversation, current_user, request, presence_map, unread_count):
    other = _get_other_participant(conversation, current_user)
    last_message = conversation.messages.order_by('-created_at').first()
    return {
        'id': conversation.id,
        'other_user': _serialize_user(other, request=request, presence_map=presence_map),
        'last_message': (last_message.content if last_message else ''),
        'last_message_at': (last_message.created_at if last_message else conversation.last_message_at),
        'unread_count': unread_count,
    }


def _ensure_can_contact(current_user, recipient):
    if recipient.id == current_user.id:
        raise PermissionDenied('Cannot contact yourself.')

    if not recipient.is_active:
        raise PermissionDenied('This account is not available for messaging.')

    allowed_user_ids = _allowed_contact_user_ids(current_user)
    if recipient.id not in allowed_user_ids:
        raise PermissionDenied('This user is not available in your authorized messaging contacts.')


def _allowed_contact_user_ids(user):
    if not user or not user.is_authenticated:
        return set()

    if user.role == CustomUser.Role.ADMIN:
        return set(
            CustomUser.objects.filter(is_active=True)
            .exclude(id=user.id)
            .values_list('id', flat=True)
        )

    admin_ids = set(
        CustomUser.objects.filter(role=CustomUser.Role.ADMIN, is_active=True)
        .exclude(id=user.id)
        .values_list('id', flat=True)
    )

    if user.role == CustomUser.Role.PATIENT:
        doctor_ids = set(
            Appointment.objects.filter(patient__user=user)
            .values_list('doctor__user_id', flat=True)
        )

        historical_partner_ids = set(
            Conversation.objects.filter(Q(participant_low=user) | Q(participant_high=user))
            .values_list('participant_low_id', 'participant_high_id')
        )
        historical_flat = {participant_id for pair in historical_partner_ids for participant_id in pair}
        historical_flat.discard(user.id)

        return admin_ids.union(doctor_ids).union(historical_flat)

    if user.role == CustomUser.Role.DOCTOR:
        patient_ids = set(
            Appointment.objects.filter(doctor__user=user)
            .values_list('patient__user_id', flat=True)
        )

        historical_partner_ids = set(
            Conversation.objects.filter(Q(participant_low=user) | Q(participant_high=user))
            .values_list('participant_low_id', 'participant_high_id')
        )
        historical_flat = {participant_id for pair in historical_partner_ids for participant_id in pair}
        historical_flat.discard(user.id)

        return admin_ids.union(patient_ids).union(historical_flat)

    return admin_ids
