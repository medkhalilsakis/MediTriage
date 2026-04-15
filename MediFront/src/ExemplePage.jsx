import { useState } from 'react';
import './ExemplePage.css';

export default function ExemplePage() {
  const [count, setCount] = useState(0);
  const [symptoms, setSymptoms] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(false);

  const handleAddSymptom = () => {
    if (inputValue.trim()) {
      setSymptoms([...symptoms, inputValue]);
      setInputValue('');
    }
  };

  const handleRemoveSymptom = (index) => {
    setSymptoms(symptoms.filter((_, i) => i !== index));
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAddSymptom();
    }
  };

  return (
    <div className={`container ${isDarkMode ? 'dark-mode' : 'light-mode'}`}>
      {/* Header */}
      <header className="header">
        <h1>🏥 MediTriage - Exemple Page</h1>
        <button 
          className="theme-toggle"
          onClick={() => setIsDarkMode(!isDarkMode)}
        >
          {isDarkMode ? '☀️ Clair' : '🌙 Sombre'}
        </button>
      </header>

      {/* Main Content */}
      <main className="main-content">
        
        {/* Section 1: Counter */}
        <section className="card">
          <h2>Compteur React</h2>
          <p>C'est un exemple simple avec useState</p>
          <div className="counter-section">
            <button 
              className="btn btn-primary"
              onClick={() => setCount(count + 1)}
            >
              Incrémenter
            </button>
            <span className="counter-display">{count}</span>
            <button 
              className="btn btn-danger"
              onClick={() => setCount(0)}
            >
              Réinitialiser
            </button>
          </div>
        </section>

        {/* Section 2: Symptom Checker */}
        <section className="card">
          <h2>Vérificateur de Symptômes</h2>
          <p>Ajoutez vos symptômes dans la liste</p>
          
          <div className="input-group">
            <input
              type="text"
              placeholder="Entrez un symptôme..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              className="input-field"
            />
            <button 
              className="btn btn-success"
              onClick={handleAddSymptom}
            >
              Ajouter
            </button>
          </div>

          {symptoms.length > 0 ? (
            <div className="symptoms-list">
              <h3>Symptômes ({symptoms.length})</h3>
              <ul>
                {symptoms.map((symptom, index) => (
                  <li key={index} className="symptom-item">
                    <span>{symptom}</span>
                    <button
                      className="btn-remove"
                      onClick={() => handleRemoveSymptom(index)}
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="empty-state">Aucun symptôme ajouté</p>
          )}
        </section>

        {/* Section 3: Info Cards */}
        <section className="card">
          <h2>Informations</h2>
          <div className="info-grid">
            <div className="info-box">
              <h3>📊 Données</h3>
              <p>Nombre de symptômes: <strong>{symptoms.length}</strong></p>
              <p>Compteur: <strong>{count}</strong></p>
            </div>
            <div className="info-box">
              <h3>⚙️ État</h3>
              <p>Mode sombre: <strong>{isDarkMode ? 'Activé' : 'Désactivé'}</strong></p>
              <p>Statut: <strong>✅ Actif</strong></p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <p>&copy; 2026 MediTriage - Exemple React avec Hooks</p>
      </footer>
    </div>
  );
}
