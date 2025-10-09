from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from dotenv import load_dotenv
import sqlite3
import requests

load_dotenv()

llm = ChatOpenAI()
search_tool = DuckDuckGoSearchRun(region="us-en")

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()

# --- LangChain built-in SQL Tools setup ---
db = SQLDatabase.from_uri("sqlite:///TEXT2SQL/students.db")  # Points to your SQLite file
sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)
sql_tools = sql_toolkit.get_tools()
# ------------------------------------------

tools = [search_tool, get_stock_price, calculator] + sql_tools
llm_with_tools = llm.bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    sql_queries: Annotated[list[str], ...]  # Track SQL queries made during conversation

def chat_node(state: ChatState):
    messages = state["messages"]
    sql_queries = state.get("sql_queries", [])
    response = llm_with_tools.invoke(messages)

    if hasattr(response, "tool_calls"):
        for tool_call in response.tool_calls:
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("tool_name")
                query_text = tool_call.get("query", "")  # Use 'query' key here
            else:
                tool_name = getattr(tool_call, "tool_name", None)
                query_text = getattr(tool_call, "query", "")

            if tool_name and tool_name.startswith("sql_db"):
                if query_text and query_text not in sql_queries:
                    sql_queries.append(query_text)

    return {
        "messages": [response],
        "sql_queries": sql_queries
    }

tool_node = ToolNode(tools)

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)

# # TESTING
CONFIG = {"configurable": {"thread_id": "thread1"}}

# Initialize with empty sql_queries list
response = chatbot.invoke(
    {
        "messages": [HumanMessage(content="who has scored the 2nd lowest percent out of 500")],
        "sql_queries": []
    },
    config=CONFIG
)

# Print only the generated content from the last message
final_message = response["messages"][-1]
print(final_message.content)

# Print all stored SQL queries generated so far
print("Generated SQL Queries:")
for q in response["sql_queries"]:
    print(q)

def retrieve_all_thread():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)
