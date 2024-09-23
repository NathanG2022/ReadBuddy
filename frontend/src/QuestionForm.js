import { useState } from 'react';
import axios from 'axios';
import { BounceLoader } from 'react-spinners';
import ReactMarkdown from 'react-markdown';
import './QuestionForm.css';
import { Button } from "@fluentui/react-components";
import { ChatRegular, DocumentAddRegular, LinkAddRegular } from "@fluentui/react-icons";

const api = axios.create({
    baseURL: 'https://nathang2022--readbuddy-backend-endpoint.modal.run'
    // baseURL: 'http://localhost:8000'
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
    const [answer, setAnswer] = useState('');
    const [documents, setDocuments] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

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

    const handleSubmit = async (e) => {
        setAnswer('');
        setIsLoading(true);
        e.preventDefault();

        // const websocket = new WebSocket('ws://localhost:8000/async_chat');
        const websocket = new WebSocket('wss://nathang2022--readbuddy-backend-endpoint.modal.run/async_chat');

        websocket.onopen = () => {
            websocket.send(question);
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.event_type === 'on_retriever_end') {
                setDocuments(data.content);
            } else if (data.event_type === 'on_chat_model_stream') {
                setAnswer(prev => prev + data.content);
            }
        };

        websocket.onclose = () => {
            setIsLoading(false);
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

    return (
        <div className="main-container">
            <form className="form">
                <input className="form-input" type="text" value={question} onChange={(e) => setQuestion(e.target.value)} />
                <div className="button-container">
                    <Button appearance="primary" icon={<ChatRegular />} style={{ backgroundColor: '#ef85c8', height: '54px', borderRadius: '3px' }} type="submit" onClick={handleSubmit}>
                        Let's Chat!
                    </Button>
                    <Button appearance="primary" icon={<LinkAddRegular />} style={{ backgroundColor: '#546fd2', height: '54px', borderRadius: '3px' }} type="submit" onClick={handleIndexing}>
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
            {isLoading && (
                <div className="loader-container">
                    <BounceLoader color="#3498db" />
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
