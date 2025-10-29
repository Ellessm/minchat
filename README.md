# minchat

10/29/2025 Early test build

Minchat - Creates a database and webui for user management and chat history that can allow multiple concurrent users to chat with a locally installed LLM on llama.cpp.



**PREREQUISITES:**  

-llama.cpp installed globally.

-an LLM in .gguf format (update .env file with appropriate model file name and directory).



**TO RUN APPLICATION:**

-clone repo

-in Terminal, change directory to minchat and run:

    ./start_llama_server.sh

-in a new terminal, cd minchat and run 

    ./setup_minchat.sh   

-in a new terminal, cd minchat/frontend and run (dev mode):

    npm install
    npm run dev

The service should now be accessible from localhost:5173
