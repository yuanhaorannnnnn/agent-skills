# Tavily Notes

## Preferred Discovery Path

Use Tavily Search as the default candidate discovery mechanism because it returns structured search results with URLs, titles, snippets, scores, and usage metadata. For latest-article requests, always verify candidate URLs by fetching the article metadata and sorting by publish date. Search ranking is not the same thing as latest order. Keep browser automation as a fallback for specific list pages, not for general search.

## Request Shape

Use `POST https://api.tavily.com/search` with a Bearer token. Useful parameters:

- `query`: search string.
- `search_depth`: use `basic` by default to control cost.
- `max_results`: maximum 20 per request.
- `include_domains`: set to `["mp.weixin.qq.com"]`.
- `start_date` / `end_date`: use when the user gives a date range.
- `include_answer`: keep false; this task needs URLs, not synthesized answers.
- `include_raw_content`: keep false; content extraction is handled by `wechat-mp-to-markdown`.

Do not invent topical keywords from previous articles. For example, do not add `Waymo` to an account-latest search unless the user explicitly asks for Waymo-related articles.

## Browser Fallback

Use Playwright only when the user provides a concrete list page such as an album URL or a page that visibly contains article links. Do not use browser automation to evade access controls.
