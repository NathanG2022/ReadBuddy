import React, { useRef, useState, useEffect } from 'react';
import './CameraComponent.css';

const baseURL = 'https://nathang2022--readbuddy-backend-endpoint.modal.run' // 'http://localhost:8000'

const CameraComponent = () => {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [processedResult, setProcessedResult] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (isCameraOpen) {
      navigator.mediaDevices
        .getUserMedia({ video: { facingMode: 'environment' } })
        .then((stream) => {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
          // Scroll to the video feed when camera opens
          containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
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

  const generateTimestampFilename = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    return `${year}${month}${day}${hours}${minutes}${seconds}.jpg`;
  };

  const dataURLtoFile = (dataurl, filename) => {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: 'image/jpeg' });
  };

  const uploadToS3 = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${baseURL}/uploadS3`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      return data.file_url;
    } catch (error) {
      console.error('Error uploading to S3:', error);
      throw error;
    }
  };

	const processImage = async (url) => {
		try {
			const payload = JSON.stringify({ url });
			console.log('Payload:', payload); // Log the payload to check its contents
	
			const response = await fetch(`${baseURL}/process_image_url`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Accept': 'application/json',
				},
				body: payload, // Ensure the body is being set correctly
			});
	
			if (!response.ok) {
				throw new Error(`Error: ${response.status} ${response.statusText}`);
			}
	
			const data = await response.json();
			return data.response;
		} catch (error) {
			console.error('Error processing image:', error);
			throw error;
		}
	};

  const handleTakePhoto = async () => {
    const context = canvasRef.current.getContext('2d');
    context.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);
    const imageDataURL = canvasRef.current.toDataURL('image/jpeg', 0.9);
    setPhoto(imageDataURL);
    setIsCameraOpen(false);
    
    try {
      setIsLoading(true);
      // Generate timestamp filename
      const filename = generateTimestampFilename();
      
      // Convert data URL to File object
      const file = dataURLtoFile(imageDataURL, filename);
      
      // Upload to S3
      const s3Url = await uploadToS3(file);
      
      // Process the image
      const result = await processImage(s3Url);
      setProcessedResult(result);
    } catch (error) {
      console.error('Error processing photo:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTakeAnotherPhoto = () => {
    setPhoto(null);
    setProcessedResult(null);
    setIsCameraOpen(true);
  };

  return (
    <div className="camera-container" ref={containerRef}>
      {!isCameraOpen && !photo && (
        <button 
          className="camera-button" 
          onClick={() => setIsCameraOpen(true)}
        >
          Open Camera
        </button>
      )}

      {isCameraOpen && (
        <>
          <div className="video-container">
            <video 
              ref={videoRef} 
              className="video-preview" 
              playsInline // Prevents full-screen mode on mobile devices
            />
          </div>
          <button 
            className="capture-button" 
            onClick={handleTakePhoto}
          >
            Capture Image
          </button>
        </>
      )}

      <canvas 
        ref={canvasRef} 
        width={640} 
        height={480} 
        style={{ display: 'none' }}
      ></canvas>

      {photo && (
        <div className="photo-container">
          <h3>Image</h3>
          <img src={photo} alt="Captured" className="captured-photo" />
          
          {isLoading && (
            <div className="loading">Processing image...</div>
          )}

          {processedResult && (
            <div className="results-container">
              <h3>Explanation</h3>
              <div className="result-text">
                {processedResult.text}
              </div>
              {processedResult.image_url && (
                <div className="result-image">
                  <h4>Illustration</h4>
                  <img 
                    src={processedResult.image_url} 
                    alt="AI Generated Illustration" 
                    className="generated-image"
                  />
                </div>
              )}
            </div>
          )}

          <button 
            className="camera-button" 
            onClick={handleTakeAnotherPhoto}
          >
            Take Another Image
          </button>
        </div>
      )}
    </div>
  );
};

export default CameraComponent;
