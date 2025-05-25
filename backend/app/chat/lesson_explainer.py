# backend/app/chat/lesson_explainer.py

from huggingface_hub import InferenceClient

# ─── Configuration ─────────────────────────────────────────────────────────────
HF_TOKEN = "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"

# Create a single InferenceClient instance.
# Default provider="auto" will pick your configured HF inference provider.
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token=HF_TOKEN
    )


def explain_lesson(
    textual_prompt: str | None = None,
    ocr_text:      str | None = None,
    max_tokens:    int  = 1024,
    temperature:    float = 0.6,
    top_p:          float = 0.9,
) -> str:
    """
    Builds a combined prompt from optional textual_prompt and ocr_text,
    sends it to Mistral-7B-v0.3 via InferenceClient, and returns the explanation.
    """
    if not (textual_prompt or ocr_text):
        raise ValueError("Provide at least one of textual_prompt or ocr_text.")

    parts = []
    if ocr_text:
        parts.append("Extracted text from your uploaded document:\n" + ocr_text)
    if textual_prompt:
        parts.append("User Prompt:\n" + textual_prompt)
    context = "\n\n".join(parts)

    prompt = (
        "You are a friendly, patient tutor. Explain the following lesson content "
        "in clear, accessible terms (as if to a student seeing this for the first time). "
        "After your explanation, invite them to ask follow-up questions.\n\n"
        f"{context}\n\n"
        "=== Begin explanation ===\n"
    )

    # NOTE: depending on your version of huggingface_hub, 
    # the method might be `.text_generation()` or `.text_generation.create()`
    result = client.text_generation(
        prompt=prompt,
        max_new_tokens= max_tokens,
        temperature= temperature,
        top_p= top_p,
        return_full_text= False,
    )

    # The returned object has a `.generated_text` attribute
    return result


if __name__ == "__main__":
    # Quick sanity check
    sample = "Explain why the angles of a triangle sum to 180 degrees."
    try:
        out = explain_lesson(textual_prompt=sample)
        print("✅ explain_lesson returned:\n", out)
    except Exception as e:
        print("❌ explain_lesson failed with:", e)