"""
AI Agent & Reasoning Core
Implements ReAct (Reason + Act) pattern with function calling for financial analysis.
Uses local Ollama with Qwen 2.5 14B model for enhanced reasoning capabilities.
"""

import httpx
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.tools import FINANCIAL_TOOLS, TOOL_DESCRIPTIONS
from app.repositories import MessageRepository, ConversationRepository

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = "http://ai-engine:11434"
MODEL_NAME = "qwen2.5:14b"  # Enhanced reasoning model

# System prompt for financial analyst persona
SYSTEM_PROMPT = """You are a professional Financial Analyst AI assistant with access to real-time market data.

YOUR CAPABILITIES:
- You can fetch live stock prices, cryptocurrency prices, IPO GMP data, and mutual fund NAVs
- You have access to historical price data and market metrics
- You provide accurate, data-driven financial analysis

IMPORTANT RULES:
1. NEVER guess or hallucinate numbers. Always use the provided tools to get real data.
2. If you need live data, you MUST call the appropriate tool before answering.
3. Clearly distinguish between factual data (from tools) and your analysis/opinions.
4. Include disclaimers: "This is not financial advice. Past performance doesn't guarantee future results."
5. Provide both simple explanations and detailed technical analysis when relevant.
6. If data fetching fails, inform the user honestly rather than making up numbers.

AVAILABLE TOOLS:
{tool_descriptions}

RESPONSE FORMAT:
When you need data, respond in this format:
THOUGHT: [Your reasoning about what data you need]
ACTION: [tool_name]
ACTION_INPUT: {{"param1": "value1", "param2": "value2"}}

After receiving tool results:
THOUGHT: [Analyze the data]
FINAL_ANSWER: [Your complete response with data, analysis, and disclaimer]

If you have all needed information:
FINAL_ANSWER: [Your response]

Remember: Accuracy over speed. Never fabricate financial data."""


class AIAgent:
    """
    AI Agent implementing ReAct pattern for financial analysis.
    Manages conversation context, tool calling, and response generation.
    """
    
    def __init__(self):
        self.ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        self.max_iterations = 5  # Prevent infinite loops
        self.context_window_size = 10  # Number of messages to include in context
    
    async def _call_ollama(self, prompt: str, stream: bool = False):
        """Send prompt to Ollama and get response."""
        try:
            payload = {
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more factual responses
                    "top_p": 0.9,
                    "num_predict": 1024
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                if stream:
                    # For streaming responses
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
            logger.error(f"Error calling Ollama: {str(e)}")
            raise
    
    def _format_context(self, chat_history: List[Dict[str, Any]]) -> str:
        """Format chat history into context string for the AI."""
        if not chat_history:
            return ""
        
        context_parts = []
        for msg in chat_history[-self.context_window_size:]:
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
            if line.startswith('THOUGHT:'):
                thought = line.replace('THOUGHT:', '').strip()
            elif line.startswith('ACTION:'):
                action = line.replace('ACTION:', '').strip()
            elif line.startswith('ACTION_INPUT:'):
                try:
                    action_input_str = line.replace('ACTION_INPUT:', '').strip()
                    action_input = json.loads(action_input_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse ACTION_INPUT: {action_input_str}")
            elif line.startswith('FINAL_ANSWER:'):
                final_answer = line.replace('FINAL_ANSWER:', '').strip()
                # Include any remaining text after FINAL_ANSWER
                if i + 1 < len(lines):
                    final_answer += '\n' + '\n'.join(lines[i+1:])
                break
        
        return thought, {action: action_input} if action and action_input else None, final_answer
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a financial data tool."""
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
        
        if tool_name not in FINANCIAL_TOOLS:
            return {"error": f"Unknown tool: {tool_name}"}
        
        tool_func = FINANCIAL_TOOLS[tool_name]
        
        try:
            # Check if tool is async
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
        
        Args:
            user_message: The user's input
            conversation_id: ID of the conversation
            user_id: ID of the user
            
        Returns:
            Dictionary with response, whether tools were used, and metadata
        """
        logger.info(f"Processing message for conversation {conversation_id}")
        
        # Save user message
        msg_repo = MessageRepository()
        await msg_repo.add_message(conversation_id, user_id, "user", user_message)
        
        # Get chat history for context
        conv_repo = ConversationRepository()
        chat_history = await conv_repo.get_chat_history(conversation_id, limit=self.context_window_size)
        
        # Format context
        context = self._format_context(chat_history)
        
        # Prepare initial prompt
        tool_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in TOOL_DESCRIPTIONS.items()])
        system_prompt = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)
        
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
            ai_response_gen = self._call_ollama(current_prompt)
            ai_response = ""
            async for chunk in ai_response_gen:
                ai_response += chunk
            logger.debug(f"AI Response: {ai_response}")
            
            # Parse response
            thought, action_dict, final_answer = self._parse_ai_response(ai_response)
            
            if final_answer:
                # AI has provided final answer
                logger.info("Final answer received")
                
                # Save assistant response
                await msg_repo.add_message(conversation_id, user_id, "assistant", final_answer)
                
                return {
                    "success": True,
                    "response": final_answer,
                    "thought_process": thought,
                    "tools_used": [tool_name for tool_name in action_dict.keys()] if action_dict else [],
                    "tool_results": tool_results,
                    "iterations": iteration
                }
            
            if action_dict:
                # AI wants to use a tool
                tool_name = list(action_dict.keys())[0]
                tool_input = action_dict[tool_name]
                
                # Execute tool
                tool_result = await self.execute_tool(tool_name, tool_input)
                tool_results.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": tool_result
                })
                
                # Append tool result to prompt for next iteration
                current_prompt += f"\n\n{ai_response}\nOBSERVATION: {json.dumps(tool_result, indent=2)}\nContinue your reasoning:"
            else:
                # No action or final answer - use raw response as fallback
                logger.warning("No action or final answer parsed, using raw response")
                final_answer = ai_response
                
                await msg_repo.add_message(conversation_id, user_id, "assistant", final_answer)
                
                return {
                    "success": True,
                    "response": final_answer,
                    "thought_process": thought,
                    "tools_used": [],
                    "tool_results": [],
                    "iterations": iteration
                }
        
        # Max iterations reached
        logger.warning("Max iterations reached without final answer")
        fallback_response = "I apologize, but I'm having trouble processing your request at the moment. Please try rephrasing your question or ask me something else."
        
        await msg_repo.add_message(conversation_id, user_id, "assistant", fallback_response)
        
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
            Dictionary chunks with response tokens
        """
        logger.info(f"Streaming response for conversation {conversation_id}")
        
        # Save user message first
        msg_repo = MessageRepository()
        await msg_repo.add_message(conversation_id, user_id, "user", user_message)
        
        # Get chat history
        conv_repo = ConversationRepository()
        chat_history = await conv_repo.get_chat_history(conversation_id, limit=self.context_window_size)
        context = self._format_context(chat_history)
        
        # For streaming, we'll use a simplified approach
        # In production, you'd implement streaming with tool calls
        
        tool_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in TOOL_DESCRIPTIONS.items()])
        system_prompt = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)
        
        prompt = f"""{system_prompt}

CURRENT CONVERSATION CONTEXT:
{context}

USER: {user_message}

Provide your analysis:"""
        
        full_response = ""
        
        try:
            async for chunk in self._call_ollama(prompt, stream=True):
                if chunk:
                    try:
                        data = json.loads(chunk)
                        token = data.get('response', '')
                        if token:
                            full_response += token
                            yield {"token": token, "done": False}
                        
                        if data.get('done', False):
                            # Save complete response
                            await msg_repo.add_message(conversation_id, user_id, "assistant", full_response)
                            yield {"token": "", "done": True, "full_response": full_response}
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            error_msg = "Sorry, I encountered an error while generating the response."
            await msg_repo.add_message(conversation_id, user_id, "assistant", error_msg)
            yield {"token": error_msg, "done": True, "error": str(e)}


# Singleton instance
ai_agent = AIAgent()
