import { useState, useRef } from 'react';
import axios from 'axios';
import { BounceLoader } from 'react-spinners';
import ReactMarkdown from 'react-markdown';
import './QuestionForm.css';
import { Button } from "@fluentui/react-components";
import { BookOpenRegular, CursorClickRegular } from "@fluentui/react-icons"; // Use a cursor icon for interactive mode

const baseURL = 'http://localhost:8000' // 'https://nathang2022--readbuddy-backend-endpoint.modal.run'
const websocketURL = 'ws://localhost:8000' // 'wss://nathang2022--rag-backend-endpoint.modal.run'

const api = axios.create({
    baseURL: baseURL
});

const Expander = ({ title, content, metadata }) => {
    const [isOpen, setIsOpen] = useState(false);
    const { source, page } = metadata; // Destructure the metadata

    // const convertUrlsToLinks = (text) => {
    //     // Refined regular expression to capture URLs, including query strings with special characters like & and =
    //     const urlRegex = /(https?:\/\/[^\s/$.?#].[^\s]*)/g;
    //     return text.split(urlRegex).map((part, index) => {
    //         // If the part is a URL, render it as a clickable link labeled "Link"
    //         if (urlRegex.test(part)) {
    //             return (
    //                 <span key={index}>
    //                     (Link: <a href={part} target="_blank" rel="noopener noreferrer">Link</a>)
    //                 </span>
    //             );
    //         }
    //         // Otherwise, render the plain text
    //         return part;
    //     });
    // };
   
    return (
        <div className="expander">
            <b onClick={() => setIsOpen(!isOpen)} className="expander-title">{title}</b>
            {isOpen && (
                <div className="expander-content">
                    {/* Convert URLs in the content to clickable links */}
                    {content}
                </div>
            )}
            {isOpen && (
                <p className="expander-content">
                    Source: {page ? (
                        <span>{source} (Page: {page})</span> // Treat it as a file
                    ) : (
                        <a href={source} target="_blank" rel="noopener noreferrer">{source}</a> // Assume it's a URL
                    )}
                </p>
            )}
        </div>
    );
};

function QuestionForm() {
    const [question, setQuestion] = useState('');
    const [response, setResponse] = useState(''); // State to store the response
    const [isLoading, setIsLoading] = useState(false);
    const [isReading, setIsReading] = useState(false); // State to toggle between "Let's Read!" and "Stop Read"
    const [answer, setAnswer] = useState('');
    const [documents, setDocuments] = useState([]);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const websocketRef = useRef(null);

    const handleReadToggle = async (e) => {
        e.preventDefault();

        if (isReading) {
            // If reading, close the WebSocket and stop
            if (websocketRef.current) {
                websocketRef.current.close();
            }
            setIsReading(false); // Toggle back to "Let's Read!"
            setIsLoading(false);  // Stop loading state
        } else {
            // Start reading (open WebSocket)
            setResponse(''); // Reset the response before the WebSocket connection
            setIsLoading(true);
            setIsReading(true); // Toggle to "Stop Read"
            
            // Open the WebSocket connection
            const websocket = new WebSocket(`${websocketURL}/async_read`);
            websocketRef.current = websocket; // Save WebSocket instance in ref

            websocket.onopen = () => {
                websocket.send(question); // Send the question to initialize the WebSocket connection
            };

            websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.event_type === 'on_image_process') {
                    setResponse(data.content); // Store the response in state
                }
            };

            websocket.onclose = () => {
                setIsReading(false); // Toggle back to "Let's Read!"
                setIsLoading(false);
            };
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();  // Prevent default form submission behavior
    
        // Prevent starting a new request if one is already in progress
        if (isLoading) {
            console.warn("A request is already in progress.");
            return;
        }

        setAnswer('');  // Reset the answer field
        setDocuments([]);  // Reset the documents field
        setIsLoading(true);  // Start loading state

        // const websocket = new WebSocket('wss://nathang2022--rag-backend-endpoint.modal.run/async_chat');
        const websocket = new WebSocket(`${websocketURL}/async_chat`);
        websocketRef.current = websocket;  // Store the WebSocket reference for future access
    
        websocket.onopen = () => {
            websocket.send(question);
        };
    
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);  // Parse the received message
            if (data.event_type === 'on_retriever_end') {
                setDocuments(data.content);  // Set the documents if received
            } else if (data.event_type === 'on_chat_model_stream') {
                setAnswer((prev) => prev + data.content);  // Append streamed content to the answer
            }
    
            // Close the WebSocket connection when the final message is received
            if (data.final) {
                websocket.close();  // Close the WebSocket connection
            }
        };
    
        // Handle WebSocket closure explicitly
        websocket.onclose = () => {
            setIsLoading(false);  // Ensure loading is stopped when the connection closes
        };
    
        // Handle any errors that occur during WebSocket communication
        websocket.onerror = (error) => {
            console.error('WebSocket Error: ', error);  // Log the error to the console
            websocket.close();  // Close the WebSocket in case of an error
            setIsLoading(false);  // Stop the loading state
        };
    };
    
    const handleIndexing = async (e) => {
        e.preventDefault();
        setAnswer('');
        setIsLoading(true);
        const response = await api.post('/indexingURL', { message: question });
        setAnswer(response.data.response);
        setIsLoading(false);
    };

    const handleIndexingDoc = async (e) => {
        const fileName = e.target.files[0].name;
        const file = e.target.files[0];
        if (!file) return;

        e.preventDefault();
        setAnswer('');
        setIsLoading(true);
        let formData = new FormData();
        formData.append("file", file, fileName);

        api.post('/indexingDoc', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Accept': 'application/json'
            }
        }).then(function (res) {
            setAnswer(`"${fileName}" uploaded successfully.`);
            setIsLoading(false);
        }).catch(function (e) {
            setIsLoading(false);
        });
    };

    const toggleMode = () => {
        if (showAdvanced) {
            setAnswer('');
            setDocuments([]);
        } else {
            setResponse('');
        }
        setShowAdvanced(!showAdvanced);
    };

    return (
        <div className="main-container">
            {/* Wrapping the toggleable buttons and content in a fixed height container */}
            <div style={{ minHeight: '150px', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}> {/* Adjust height as needed */}
                {/* Toggle Button to switch modes */}
                <Button
                    appearance="secondary"
                    icon={showAdvanced ? <BookOpenRegular /> : <CursorClickRegular />} // Different icons for each mode
                    style={{
                        backgroundColor: showAdvanced ? '#ff69b4' : '#6c63ff',  // Pink for Quiet Reading, Purple for Interactive
                        height: '30px',
                        borderRadius: '6px',      // Rounded frame
                        color: '#fff',             // White text color for both modes
                        border: '2px solid',       // Border with dynamic color
                        borderColor: showAdvanced ? '#ff69b4' : '#6c63ff', // Border matching background
                        padding: '5px 10px',      // Padding for the button
                        fontSize: '18px',          // Smaller font size for text
                        marginBottom: '14px',      // Space below the button
                        cursor: 'pointer'          // Cursor pointer for hover effect
                    }}
                    onClick={toggleMode}
                >
                    {showAdvanced ? "Switch to Quiet Reading Mode" : "Switch to Interactive Reading Mode"}
                </Button>

                {/* Mode-specific icon and button */}
                {!showAdvanced && (
                    <div className="button-container">
                        <Button 
                            appearance="primary"
                            style={{ backgroundColor: '#ef85c8'}}
                            type="submit"
                            onClick={handleReadToggle}
                        >
                            {isReading ? 'Stop Read' : "Let's Read!"}
                        </Button>
                    </div>
                )}

                {showAdvanced && (
                    <form className="form">
                        <input
                            className="form-input"
                            type="text"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="Enter your question or topic"
                        />
                        <div className="button-container" >
                            <Button
                                appearance="primary"
                                style={{ backgroundColor: '#ef85c8'}}
                                type="submit"
                                onClick={handleSubmit}
                            >
                                Chat
                            </Button>
                            <Button
                                appearance="primary"
                                style={{ backgroundColor: '#546fd2'}}
                                type="submit"
                                onClick={handleIndexing}
                            >
                                Add Webpage
                            </Button>
                            <div>
                                <label htmlFor="file-upload" className="custom-file-upload">
                                    Add Docs
                                </label>
                                <input id="file-upload" type="file" onInput={handleIndexingDoc} />
                            </div>
                        </div>
                    </form>
                )}
            </div>

            {isLoading && (
                <div className="loader-container">
                    <BounceLoader color="#3498db" />
                </div>
            )}

            {!showAdvanced && response && (
                <div className="response-container">
                    {/* Render the extracted text */}
                    {response.text && (
                        <div className="response-container">
                            <p>{response.text}</p>
                        </div>
                    )}

                    {/* Render the generated image */}
                    {response.image_url && (
                        <div className="image-container">
                            <img src={response.image_url} alt="Generated Image" className="centered-image" />
                        </div>
                    )}
                </div>
            )}

            {answer && (
                <div className="results-container">
                    <div className="results-answer">
                        <h2>Answer:</h2>
                        <ReactMarkdown>{answer}</ReactMarkdown>
                    </div>
                    {documents?.length ? (
                        <div className="results-documents">
                            <h2>References:</h2>
                            <ul>
                                {documents.map((document, index) => (
                                    <Expander 
                                        key={index} 
                                        title={document.page_content.split(" ").slice(0, 5).join(" ") + "..."} 
                                        content={document.page_content} 
                                        metadata={document.metadata} />
                                ))}
                            </ul>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    );
}

export default QuestionForm;
