import { useState, useRef } from 'react';
import axios from 'axios';
import { BounceLoader } from 'react-spinners';
import ReactMarkdown from 'react-markdown';
import './QuestionForm.css';
import { Button } from "@fluentui/react-components";
import { BookOpenRegular, DocumentAddRegular, LinkAddRegular } from "@fluentui/react-icons";

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
    const websocketRef = useRef(null); // Use ref to store the WebSocket instance

    // const handleSubmit = async (e) => {
    //     setAnswer('');
    //     setIsLoading(true);
    //     e.preventDefault();
    //     console.log("Your question: ", question);
    //     console.log("Calling backend at ", api.defaults.baseURL)
    //     const response = await api.post('/chat', { message: question });
    //     setAnswer(response.data.answer);

    //     setDocuments(response.data.documents)
    //     setIsLoading(false);
    // }

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
        setAnswer('');
        setIsLoading(true);
        e.preventDefault();

        const websocket = new WebSocket('wss://nathang2022--rag-backend-endpoint.modal.run/async_chat');

        websocket.onopen = () => {
            websocket.send(question);
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event_type === 'on_retriever_end') {
                setDocuments(data.content);
            } else if (data.event_type === 'on_chat_model_stream') {
                setAnswer((prev) => prev + data.content);
            }
        };

        websocket.onclose = () => {
            setIsLoading(false);
        };
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

    return (
        <div className="main-container">
            {/* New line for "Let's Read!" / "Stop Read" button */}
            <h2>Welcome to AI Agent for Neurodivergent!</h2>
            <Button
                appearance="primary"
                icon={<BookOpenRegular />}
                style={{ backgroundColor: '#ef85c8', height: '54px', borderRadius: '3px', marginBottom: '20px' }}
                type="submit"
                onClick={handleReadToggle}
            >
                {isReading ? 'Stop Read' : "Let's Read!"}
            </Button>

            <form className="form">
                <input 
                    className="form-input" 
                    type="text" 
                    value={question} 
                    onChange={(e) => setQuestion(e.target.value)} 
                    placeholder="Enter your question or topic"
                />
                <div className="button-container">
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

            {/* Show loader while waiting */}
            {isLoading && (
                <div className="loader-container">
                    <BounceLoader color="#3498db" />
                </div>
            )}

            {/* Render the paragraph when available */}
            {paragraph && (
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
