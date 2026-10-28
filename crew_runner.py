
    # Search only when the task appears to need external research.
    logger.info("[DEBUG] Checking whether web search is needed")
    search_started = time.time()

    task_lower = user_task.lower()

    research_keywords = (
        "latest", "current", "today", "news", "research",
        "search the web", "find sources", "citations",
        "references", "verify", "fact-check", "recent",
        "2026", "2025", "compare websites"
    )

    needs_search = any(
        keyword in task_lower for keyword in research_keywords
    )

    if needs_search:
        logger.info("[DEBUG] Web search required")

        try:
            search_results = search_web(
                "Research this task using reliable sources. "
                "Prefer official sources. Return concise evidence and URLs. "
                "Do not invent sources or verification.\n\n"
                f"USER TASK:\n{user_task}"
            )
        except Exception as exc:
            logger.exception("[DEBUG] Web search failed")
            search_results = (
                '{"status":"ERROR","search_response":"",'
                '"error":"Search unavailable: '
                + type(exc).__name__
                + '. Do not invent evidence."}'
            )
    else:
        logger.info("[DEBUG] Skipping web search for this task")
        search_results = (
            '{"status":"SKIPPED","search_response":'
            '"External research was not requested. '
            'Use model knowledge and disclose uncertainty when needed."}'
        )

    logger.info(
        "[DEBUG] Search decision completed in %.1f seconds",
        time.time() - search_started,
    )
