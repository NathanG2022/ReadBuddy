import React from 'react';
import './App.css';
import CameraComponent from './CameraComponent';

function App() {
  return (
    <div className="App">
      <header className="App-header">
      <img src={`${process.env.PUBLIC_URL}/logo192.png`} alt="Company Logo" className="App-logo" />
      </header>
      <CameraComponent />
    </div>
  );
}

export default App;
