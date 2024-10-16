import { useState, useRef } from 'react';
import axios from 'axios';
import { BounceLoader } from 'react-spinners';
import ReactMarkdown from 'react-markdown';
import './QuestionForm.css';
import { Button } from "@fluentui/react-components";
import { BookOpenRegular, DocumentAddRegular, LinkAddRegular, CursorClickRegular } from "@fluentui/react-icons"; // Use a cursor icon for interactive mode

const api = axios.create({
    // baseURL: 'https://nathang2022--readbuddy-backend-endpoint.modal.run'
    baseURL: 'http://localhost:8000'
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
    const [paragraph, setParagraph] = useState(''); // State to store the paragraph response
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
            setParagraph(null); // Reset the response before the WebSocket connection
            setIsLoading(true);
            setIsReading(true); // Toggle to "Stop Read"
            
            // Open the WebSocket connection
            const websocket = new WebSocket('ws://localhost:8000/async_chat');
            websocketRef.current = websocket; // Save WebSocket instance in ref

            websocket.onopen = () => {
                console.log("WebSocket connection established.");
                websocket.send(question); // Send the question to initialize the WebSocket connection
            };

            websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.event_type === 'on_image_process') {
                    setParagraph(data.content); // Store the response in state
                }
            };

            websocket.onclose = () => {
                console.log("WebSocket connection closed.");
                setIsReading(false); // Toggle back to "Let's Read!"
                setIsLoading(false);
            };
        }
    };

    const handleSubmit = async (e) => {
        setAnswer('');  // Reset the answer field
        setDocuments([]);  // Reset the documents field
        setIsLoading(true);  // Start loading state
        e.preventDefault();  // Prevent default form submission behavior
    
        // Open a new WebSocket connection to the backend
        const websocket = new WebSocket('ws://localhost:8000/async_chat');  // Use your local WebSocket endpoint
        websocketRef.current = websocket;  // Store the WebSocket reference for future access
    
        websocket.onopen = () => {
            // Send the question to the server once the connection is open
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
                console.log('Final message received, closing WebSocket');
                websocket.close();  // Close the WebSocket connection
                setIsLoading(false);  // Stop the loading state
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

        // Fallback to manually close the WebSocket connection after a timeout (e.g., 30 seconds)
        setTimeout(() => {
            if (websocket.readyState === WebSocket.OPEN) {
                console.log('Timeout reached, closing WebSocket connection');  // Debugging log
                websocket.close();  // Forcefully close the WebSocket connection
                setIsLoading(false);  // Stop the loading state
            }
        }, 15000);  // Close the connection after 30 seconds (adjust as needed)
    };
    
    const handleIndexing = async (e) => {
        e.preventDefault();
        setParagraph(null);
        setIsLoading(true);
        const response = await api.post('/indexingURL', { message: question });
        setParagraph(response.data.response);
        setIsLoading(false);
    };

    const handleIndexingDoc = async (e) => {
        const fileName = e.target.files[0].name;
        const file = e.target.files[0];
        if (!file) return;

        e.preventDefault();
        setParagraph(null);
        setIsLoading(true);
        let formData = new FormData();
        formData.append("file", file, fileName);

        api.post('/indexingDoc', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Accept': 'application/json'
            }
        }).then(function (res) {
            setParagraph(`"${fileName}" uploaded successfully.`);
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
            setParagraph('');
        }
        setShowAdvanced(!showAdvanced);
    };

    return (
        <div className="main-container">
            {/* Wrapping the toggleable buttons and content in a fixed height container */}
            <div style={{ minHeight: '300px', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}> {/* Adjust height as needed */}
                {/* Toggle Button to switch modes */}
                <br/>
                <Button
                    appearance="secondary"
                    icon={showAdvanced ? <BookOpenRegular /> : <CursorClickRegular />} // Different icons for each mode
                    style={{
                        backgroundColor: showAdvanced ? '#ff69b4' : '#6c63ff',  // Pink for Quiet Reading, Purple for Interactive
                        height: '40px',
                        borderRadius: '30px',      // Rounded frame
                        color: '#fff',             // White text color for both modes
                        border: '2px solid',       // Border with dynamic color
                        borderColor: showAdvanced ? '#ff69b4' : '#6c63ff', // Border matching background
                        padding: '5px 15px',      // Padding for the button
                        fontSize: '18px',          // Smaller font size for text
                        marginBottom: '20px',      // Space below the button
                        cursor: 'pointer'          // Cursor pointer for hover effect
                    }}
                    onClick={toggleMode}
                >
                    {showAdvanced ? "Switch to Quiet Reading Mode" : "Switch to Interactive Reading Mode"}
                </Button>
                <br/>
                <br/>

                {/* Mode-specific icon and button */}
                {!showAdvanced && (
                    <Button
                        appearance="primary"
                        icon={<BookOpenRegular />} // Icon for quiet reading mode
                        style={{ backgroundColor: '#ef85c8', height: '54px', borderRadius: '3px', marginBottom: '20px' }}
                        type="submit"
                        onClick={handleReadToggle}
                    >
                        {isReading ? 'Stop Read' : "Let's Read!"}
                    </Button>
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
                                icon={<BookOpenRegular />}
                                style={{ backgroundColor: '#ef85c8', height: '54px', borderRadius: '3px' }}
                                type="submit"
                                onClick={handleSubmit}
                            >
                                Submit
                            </Button>
                            <Button
                                appearance="primary"
                                icon={<LinkAddRegular />}
                                style={{ backgroundColor: '#546fd2', height: '54px', borderRadius: '3px' }}
                                type="submit"
                                onClick={handleIndexing}
                            >
                                Add Webpage
                            </Button>
                            <div>
                                <label htmlFor="file-upload" className="custom-file-upload">
                                    <DocumentAddRegular /> Add Docs
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

            {!showAdvanced && paragraph && (
                <div className="results-container">
                    <p>{paragraph}</p>
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
