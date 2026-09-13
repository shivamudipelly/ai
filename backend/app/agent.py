"""
AI Agent & Reasoning Core
Implements ReAct (Reason + Act) pattern with function calling for financial analysis.
Uses local Ollama with Qwen 2.5 model for enhanced reasoning capabilities.
"""

import httpx
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

from app.config import settings
from app.tools import FINANCIAL_TOOLS, TOOL_DESCRIPTIONS
from app.repositories import MessageRepository, ConversationRepository
from app.models import Message

logger = logging.getLogger(__name__)

# System prompt for financial analyst persona (date injected at runtime)
SYSTEM_PROMPT = """You are a professional Financial Analyst AI assistant with access to real-time market data tools.

TODAY'S DATE: {today_date}

CRITICAL RULES — NEVER BREAK THESE:
1. TODAY IS {today_date}. Never say any other date. Never say it is 2023 or 2024.
2. NEVER fabricate, guess, or hallucinate any prices, numbers, percentages, or market data.
3. If a tool returns an error or no data, say honestly: "I could not fetch live data for [X] right now."
4. ALWAYS call the appropriate tool FIRST before stating any price or financial figure.
5. For Indian stocks (NSE/BSE), use the ticker with .NS suffix (e.g. TCS.NS, RELIANCE.NS). Always show prices in INR.
6. For Indian stocks, NEVER show prices in USD unless the tool explicitly returns USD.
7. Keep your FINAL_ANSWER concise — maximum 4-5 sentences. Do NOT repeat sentences.
8. Never repeat the same sentence or phrase more than once in a response.

AVAILABLE TOOLS:
{tool_descriptions}

RESPONSE FORMAT:
When you need data, respond in this format:
THOUGHT: [What data you need and which tool to use]
ACTION: [exact_tool_name]
ACTION_INPUT: {{"param1": "value1"}}

After receiving tool results:
THOUGHT: [Brief analysis of the data]
FINAL_ANSWER: [Concise response with the real data from the tool. Maximum 4-5 sentences. No repetition.]

If no tool needed:
FINAL_ANSWER: [Your response]

IMPORTANT: Your FINAL_ANSWER must be SHORT and NOT repeat any sentences. Stop after 4-5 sentences."""


class AIAgent:
    """
    AI Agent implementing ReAct pattern for financial analysis.
    Manages conversation context, tool calling, and response generation.
    """
    
    def __init__(self):
        self.max_iterations = 5  # Prevent infinite loops
        self.context_window_size = getattr(settings, 'max_context_messages', 10)
    
    @property
    def ollama_url(self) -> str:
        return f"{settings.ollama_host.rstrip('/')}/api/generate"

    @property
    def model_name(self) -> str:
        return settings.ollama_model
    
    async def _call_ollama(self, prompt: str, stream: bool = False):
        """Send prompt to Ollama and get response."""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 512,
                    "stop": ["USER:", "HUMAN:", "\n\nUSER", "\n\nHUMAN"]
                }
            }
            
            timeout = httpx.Timeout(getattr(settings, 'ollama_timeout', 120.0), connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                if stream:
                    async with client.stream("POST", self.ollama_url, json=payload) as response:
                        async for line in response.aiter_lines():
                            if line:
                                yield line
                else:
                    response = await client.post(self.ollama_url, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    yield result.get('response', '')
                    
        except Exception as e:
            logger.error(f"Error calling Ollama at {self.ollama_url}: {str(e)}")
            raise
    
    def _format_context(self, chat_history: List[Union[Message, Dict[str, Any]]]) -> str:
        """Format chat history into context string for the AI."""
        if not chat_history:
            return ""
        
        context_parts = []
        for msg in chat_history[-self.context_window_size:]:
            if isinstance(msg, Message):
                role = "User" if msg.role == "user" else "Assistant"
                content = msg.content
            else:
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)
    
    def _parse_ai_response(self, response: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        Parse AI response to extract thought, action, and final answer.
        
        Returns:
            Tuple of (thought, action_input_dict, final_answer)
        """
        thought = None
        action = None
        action_input = None
        final_answer = None
        
        lines = response.strip().split('\n')
        
        for i, line in enumerate(lines):
            line_str = line.strip()
            if line_str.startswith('THOUGHT:'):
                thought = line_str.replace('THOUGHT:', '').strip()
            elif line_str.startswith('ACTION:'):
                action = line_str.replace('ACTION:', '').strip()
            elif line_str.startswith('ACTION_INPUT:'):
                try:
                    action_input_str = line_str.replace('ACTION_INPUT:', '').strip()
                    action_input = json.loads(action_input_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse ACTION_INPUT: {line_str}")
            elif line_str.startswith('FINAL_ANSWER:'):
                final_answer = line_str.replace('FINAL_ANSWER:', '').strip()
                if i + 1 < len(lines):
                    final_answer += '\n' + '\n'.join(lines[i+1:])
                break
        
        return thought, {action: action_input} if (action and action_input is not None) else None, final_answer
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a financial data tool."""
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
        
        if tool_name not in FINANCIAL_TOOLS:
            return {"error": f"Unknown tool: {tool_name}"}
        
        tool_func = FINANCIAL_TOOLS[tool_name]
        
        try:
            import inspect
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**tool_input)
            else:
                result = tool_func(**tool_input)
            
            logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"error": str(e)}
    
    async def process_message(
        self,
        user_message: str,
        conversation_id: str,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Process user message using ReAct pattern.
        """
        logger.info(f"Processing message for conversation {conversation_id}")
        
        # Save user message
        await MessageRepository.add_message(conversation_id, user_id, "user", user_message)
        
        # Get chat history for context
        chat_history = await MessageRepository.get_messages_by_conversation(conversation_id, limit=self.context_window_size)
        
        # Format context
        context = self._format_context(chat_history)
        
        # Prepare initial prompt with today's real date
        tool_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in TOOL_DESCRIPTIONS.items()])
        today_date = datetime.now().strftime("%A, %d %B %Y")  # e.g. "Saturday, 13 September 2026"
        system_prompt = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions, today_date=today_date)
        
        initial_prompt = f"""{system_prompt}

CURRENT CONVERSATION CONTEXT:
{context}

USER: {user_message}

Begin your reasoning:"""
        
        # ReAct loop
        iteration = 0
        current_prompt = initial_prompt
        tool_results = []
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"ReAct iteration {iteration}")
            
            # Get AI response
            try:
                ai_response_gen = self._call_ollama(current_prompt)
                ai_response = ""
                async for chunk in ai_response_gen:
                    ai_response += chunk
            except Exception as e:
                logger.error(f"Failed to communicate with AI engine: {e}")
                fallback_msg = "Unable to connect to AI engine. Please ensure Ollama is running."
                await MessageRepository.add_message(conversation_id, user_id, "assistant", fallback_msg)
                return {
                    "success": False,
                    "response": fallback_msg,
                    "error": str(e),
                    "tools_used": [],
                    "tool_results": [],
                    "iterations": iteration
                }

            logger.debug(f"AI Response: {ai_response}")
            
            # Parse response
            thought, action_dict, final_answer = self._parse_ai_response(ai_response)
            
            if final_answer:
                logger.info("Final answer received")
                await MessageRepository.add_message(conversation_id, user_id, "assistant", final_answer)
                return {
                    "success": True,
                    "response": final_answer,
                    "thought_process": thought,
                    "tools_used": [tool_name for tool_name in action_dict.keys()] if action_dict else [],
                    "tool_results": tool_results,
                    "iterations": iteration
                }
            
            if action_dict:
                tool_name = list(action_dict.keys())[0]
                tool_input = action_dict[tool_name]
                
                tool_result = await self.execute_tool(tool_name, tool_input or {})
                tool_results.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": tool_result
                })
                
                current_prompt += f"\n\n{ai_response}\nOBSERVATION: {json.dumps(tool_result, indent=2)}\nContinue your reasoning:"
            else:
                logger.warning("No action or final answer parsed, using raw response")
                final_answer = ai_response.strip() or "Analysis complete."
                await MessageRepository.add_message(conversation_id, user_id, "assistant", final_answer)
                return {
                    "success": True,
                    "response": final_answer,
                    "thought_process": thought,
                    "tools_used": [],
                    "tool_results": [],
                    "iterations": iteration
                }
        
        logger.warning("Max iterations reached without final answer")
        fallback_response = "I apologize, but I'm having trouble completing this multi-step reasoning task. Please try rephrasing your question."
        await MessageRepository.add_message(conversation_id, user_id, "assistant", fallback_response)
        
        return {
            "success": False,
            "response": fallback_response,
            "error": "Max iterations reached",
            "tools_used": [tr["tool"] for tr in tool_results],
            "tool_results": tool_results,
            "iterations": iteration
        }
    
    async def stream_response(
        self,
        user_message: str,
        conversation_id: str,
        user_id: str = "default_user"
    ):
        """
        Stream AI response token by token.
        
        Yields:
            Dictionary chunks with response tokens in expected SSE format:
            {"type": "content", "content": token, "token": token, "done": False}
        """
        logger.info(f"Streaming response for conversation {conversation_id}")
        
        # Save user message first
        await MessageRepository.add_message(conversation_id, user_id, "user", user_message)
        
        # Get chat history
        chat_history = await MessageRepository.get_messages_by_conversation(conversation_id, limit=self.context_window_size)
        context = self._format_context(chat_history)
        
        tool_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in TOOL_DESCRIPTIONS.items()])
        today_date = datetime.now().strftime("%A, %d %B %Y")
        system_prompt = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions, today_date=today_date)
        
        prompt = f"""{system_prompt}

CURRENT CONVERSATION CONTEXT:
{context}

USER: {user_message}

Provide your analysis (be concise, max 4-5 sentences, no repetition):"""
        
        full_response = ""
        
        try:
            async for chunk in self._call_ollama(prompt, stream=True):
                if chunk:
                    try:
                        data = json.loads(chunk)
                        token = data.get('response', '')
                        if token:
                            full_response += token
                            yield {
                                "type": "content",
                                "content": token,
                                "token": token,
                                "done": False
                            }
                        
                        if data.get('done', False):
                            # Clean up final response text if needed
                            clean_response = full_response
                            if "FINAL_ANSWER:" in clean_response:
                                clean_response = clean_response.split("FINAL_ANSWER:", 1)[-1].strip()
                            
                            await MessageRepository.add_message(conversation_id, user_id, "assistant", clean_response or full_response)
                            yield {
                                "type": "done",
                                "content": "",
                                "token": "",
                                "done": True,
                                "full_response": clean_response or full_response
                            }
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            error_msg = "Sorry, I encountered an error while generating the response."
            await MessageRepository.add_message(conversation_id, user_id, "assistant", error_msg)
            yield {
                "type": "error",
                "content": error_msg,
                "token": error_msg,
                "done": True,
                "error": str(e)
            }


# Singleton instance
ai_agent = AIAgent()
