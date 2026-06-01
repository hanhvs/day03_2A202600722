#!/usr/bin/env python3
"""Local demo for @hanhvs tasks (chatbot + agent catalog tools)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.chatbot.chatbot_baseline import DEMO_QUERIES, run_chatbot
from src.core.llm_factory import get_llm_from_env
from src.tools import TOOL_SPECS


def main():
    load_dotenv()
    llm = get_llm_from_env()
    query = DEMO_QUERIES[0]

    print("=== Chatbot baseline ===")
    print(run_chatbot(llm, query))

    print("\n=== ReAct Agent (needs API; 4 tools when partner merges) ===")
    agent = ReActAgent(llm=llm, tools=TOOL_SPECS)
    print(agent.run(query))


if __name__ == "__main__":
    main()
