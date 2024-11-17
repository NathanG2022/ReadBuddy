import React, { useRef, useState, useEffect } from 'react';
import './CameraComponent.css';

const CameraComponent = () => {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [photo, setPhoto] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (isCameraOpen) {
      navigator.mediaDevices
        .getUserMedia({ video: { facingMode: 'environment' } })
        .then((stream) => {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        })
        .catch((err) => {
          console.error('Error accessing camera: ', err);
        });
    } else {
      if (videoRef.current && videoRef.current.srcObject) {
        let stream = videoRef.current.srcObject;
        let tracks = stream.getTracks();
        tracks.forEach((track) => track.stop());
        videoRef.current.srcObject = null;
      }
    }
  }, [isCameraOpen]);

  const handleTakePhoto = () => {
    const context = canvasRef.current.getContext('2d');
    context.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);
    const imageDataURL = canvasRef.current.toDataURL('image/png');
    setPhoto(imageDataURL);
    setIsCameraOpen(false);
  };

  const handleTakeAnotherPhoto = () => {
    setPhoto(null);
    setIsCameraOpen(true);
  };

  return (
    <div className="camera-container">
      {!isCameraOpen && !photo && (
        <button 
          className="camera-button" 
          onClick={() => setIsCameraOpen(true)}
        >
          Open Camera
        </button>
      )}

      {isCameraOpen && (
        <div className="video-container">
          <video 
            ref={videoRef} 
            className="video-preview" 
            width="640" 
            height="480"
          />
          <button 
            className="camera-button capture" 
            onClick={handleTakePhoto}
          >
            Capture Photo
          </button>
        </div>
      )}

      <canvas 
        ref={canvasRef} 
        width={640} 
        height={480} 
        style={{ display: 'none' }}
      ></canvas>

      {photo && (
        <div className="photo-container">
          <h3>Captured Photo</h3>
          <img src={photo} alt="Captured" />
          <button 
            className="camera-button" 
            onClick={handleTakeAnotherPhoto}
          >
            Take Another Photo
          </button>
        </div>
      )}
    </div>
  );
};

export default CameraComponent;
