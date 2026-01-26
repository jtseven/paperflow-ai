import logging
import random
import traceback
from typing import Any

from django.conf import settings
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_community.callbacks import get_openai_callback
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from documents.embeddings import DocumentEmbeddings
from documents.models import Document

logger = logging.getLogger("paperless.ai_chat")
embeddings = DocumentEmbeddings()


@tool
def search_documents(query: str) -> tuple[str, list[str]]:
    """Search for relevant documents using semantic similarity"""
    try:
        # Get most relevant documents for the query
        search_results = embeddings.vector_store.similarity_search(
            query,
            k=3,  # Retrieve top 3 most relevant chunks
            return_metadata=True,
            return_all=True,
        )
        if len(search_results) == 0:
            logger.warning(
                "No relevant documents found using embedding similarity search!"
            )
            return "", []
        logger.info(
            f"Found {len(search_results)} relevant vector store entries for query."
        )

        # Extract content from the search results
        # logger.info(search_results[0])
        context_texts = [doc.page_content for doc in search_results]
        document_ids = [doc.metadata.get("document_id") for doc in search_results]
        documents = [Document.objects.get(pk=id) for id in document_ids]
        context = "\n\n".join(
            str(
                {
                    "title": doc.title,
                    "id": doc.pk,
                    "content": context_text,
                    "link": f"{settings.PAPERLESS_URL}/documents/{doc.pk}/",
                },
            )
            for doc, context_text in zip(documents, context_texts)
        )
        # Get document IDs
        # TODO fix this unnecessary (?) duplication
        document_ids = []
        for doc in search_results:
            doc_id = doc.metadata.get("document_id")
            if doc_id:
                document_ids.append(str(doc_id))

        logger.info(f"Retrieved {len(context_texts)} relevant document chunks")
        return context, document_ids

    except Exception as e:
        logger.error(f"Error searching vector store: {e!s}")
        traceback.print_exc()
        return "", []


SYSTEM_PROMPT = """You are a helpful assistant for a document management system.
    Answer the user's question based on information from the user's documents and the conversation history.
    Use the 'search_documents' tool to find relevant information in the user's documents.
    If you are not able to find relevant information, say so politely and do not make up any information.
    Formulate your answer in the same language as the question.
    You can use markdown to format your answer.
    Cite the documents in your answer using numbers counting up from one like '[1]'. Place the citations directly after the corresponding information in your answer.
    On the bottom of your answer give a list of references for each document you cited using Markdown links with the following format (do not show the link text, just the document title and link to the corresponding document using the links and titles given in the search tool response):

    [1]: [title](link)
    [2]: [title](link)
    [3]: [title](link)
    If you are citing different chunks from the same document (same id), use the same citation number for each chunk.
    """
model = init_chat_model(
    model=settings.CHAT_MODEL_NAME,
    api_key=settings.OPENAI_API_KEY.get_secret_value(),
)
agent = create_agent(
    model=model,
    tools=[search_documents],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),
)


def process_question(
    question: str,
    user_id: int,
    session_id: str | None = None,
) -> tuple[str, str]:
    """
    Process a user question through the chat agent and handle chat history.

    Args:
        question: The user's question
        user_id: The ID of the user asking the question
        session_id: Optional session ID for conversation continuity

    Returns:
        Tuple of (reply, document_ids, session_id)
    """

    # Get or create session ID
    if not session_id:
        session_id = f"{user_id}_{random.randint(1, 1000000)}"

    input = {"messages": [HumanMessage(content=(question))]}

    try:
        # Run the chat graph
        with get_openai_callback() as cb:
            response = agent.invoke(input, {"configurable": {"thread_id": session_id}})
            logger.info(
                f"OpenAI API usage: {cb.total_tokens} tokens, cost: ${cb.total_cost}",
            )

        # Get the last AI message
        ai_answer = response["messages"][-1].content

        return ai_answer, session_id

    except Exception as e:
        logger.error(f"Error in chat: {type(e)}: {e!s}")
        logger.error(traceback.format_exc())
        return "An error occurred while generating the answer", session_id


def clear_chat_history(session_id: str) -> bool:
    """
    Clear the chat history for a specific session.

    Args:
        session_id: The session ID to clear history for

    Returns:
        Boolean indicating success
    """
    logger.info(f"Clearing chat history for session: {session_id}")
    try:
        # agent.get_state()
        logger.info(f"Cleared chat history for session: {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error clearing chat history: {e!s}")
        return False


def get_chat_messages(session_id: str) -> list[dict[str, Any]]:
    """
    Get the formatted chat messages for a specific session.

    Args:
        session_id: The session ID to get messages for

    Returns:
        List of message dictionaries in the format expected by the frontend
    """
    try:
        messages = agent.get_state(
            {"configurable": {"thread_id": session_id}},
        ).values.get(
            "messages",
            [],
        )
        if not messages:
            logger.info(f"No chat history found for session: {session_id}")
            return []
        else:
            logger.info(
                f"Found {len(messages)} messages in chat history for session: {session_id}",
            )
        text_messages = []
        for message in messages:
            if isinstance(message, HumanMessage) and message.content:
                text_messages.append(
                    {
                        "text": message.content,
                        "fromUser": True,
                    },
                )
            elif isinstance(message, AIMessage) and message.content:
                text_messages.append(
                    {
                        "text": message.content,
                        "fromUser": False,
                    },
                )
        return text_messages
    except Exception as e:
        logger.error(f"Error getting chat messages: {e!s}")
        logger.error(traceback.format_exc())
        return []
