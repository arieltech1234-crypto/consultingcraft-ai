import re
import time

def chat_completion(client, model, messages, temperature=0.7, max_tokens=2048, max_retries=3, **kwargs):
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    """Call Groq chat completions, clamping max_tokens if the model rejects it."""
    requested = max_tokens
    attempt = 0
    while attempt < max_retries:
        try:
            print(f"DEBUG: Calling Groq with model {model}...")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=requested, **kwargs,
            )
            print(f"DEBUG: Groq response length: {len(response.choices[0].message.content)}")
            return response
        except Exception as e:
            error_str = str(e)
            print(f"DEBUG: Groq API Error: {error_str}")
            
            # Handle max tokens clamped
            match = re.search(
                r"`max_tokens` must be less than or equal to `(\d+)`",
                error_str,
            )
            if match:
                allowed = int(match.group(1))
                if allowed < requested:
                    requested = allowed
                    continue
                    
            # Handle rate limits
            if ("429" in error_str or "413" in error_str or "rate_limit_exceeded" in error_str) and attempt < max_retries - 1:
                # TPM limits reset every minute, so we need to wait a full minute
                wait_time = 62
                print(f"DEBUG: Rate limit hit. Sleeping {wait_time}s before retry {attempt + 1}/{max_retries}...")
                try:
                    import streamlit as st
                    from streamlit.runtime.scriptrunner import get_script_run_ctx
                    if get_script_run_ctx():
                        st.toast(f"API Rate Limit (TPM) hit. Pausing {wait_time}s to reset...", icon="⏳")
                except ImportError:
                    pass
                time.sleep(wait_time)
                attempt += 1
                continue
                
            raise
