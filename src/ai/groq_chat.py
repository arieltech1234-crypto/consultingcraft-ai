import logging
import re
import time

logger = logging.getLogger(__name__)


def chat_completion(client, model, messages, temperature=0.7, max_tokens=2048, max_retries=3, **kwargs):
    """Call Groq chat completions, clamping max_tokens and retrying on rate limits."""
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    requested = max_tokens
    attempt = 0
    while attempt < max_retries:
        try:
            logger.debug("Calling Groq with model %s", model)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=requested, **kwargs,
            )
            logger.debug("Groq response length: %d", len(response.choices[0].message.content or ""))
            return response
        except Exception as e:
            error_str = str(e)
            logger.debug("Groq API error: %s", error_str)

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
                logger.warning("Rate limit hit. Sleeping %ds before retry %d/%d...", wait_time, attempt + 1, max_retries)
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


def chat_completion_text(client, model, prompt, temperature=0.7, max_tokens=1500, max_retries=3) -> str:
    """Convenience wrapper for the common single-user-message, text-out call pattern."""
    response = chat_completion(
        client,
        model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=max_retries,
    )
    return response.choices[0].message.content
