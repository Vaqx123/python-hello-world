from http.server import BaseHTTPRequestHandler
from crawl4ai import (
    AsyncWebCrawler, BrowserConfig, CrawlerRunConfig,
    CacheMode, DefaultMarkdownGenerator,
    PruningContentFilter, BM25ContentFilter, CrawlResult
)
import asyncio
import json
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        query = query_params.get('query', [None])[0]  # Get first 'query' value or None

        # Error if 'query' is missing
        if not query:
            self.send_error(400, "Missing required parameter: 'query'")
            return

        # Run async crawler
        try:
            result = asyncio.run(self.crawl(query))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "markdown": result.markdown.fit_markdown
            }).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Crawler failed: {str(e)}")

    async def crawl(self, query: str) -> CrawlResult:
        browser_config = BrowserConfig(headless=True, verbose=True)
        bm25_filter = BM25ContentFilter(user_query=query, bm25_threshold=1.2)
        pr = PruningContentFilter(threshold=0.5, threshold_type="dynamic")

        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                exclude_external_links=True,
                markdown_generator=DefaultMarkdownGenerator(
                    options={"ignore_links": True},
                    content_filter=pr
                ),
                js_code='''const div = Array.from(document.querySelectorAll('div'))
                    .find(div => div.textContent.trim() === "Price - Low To High");
                    if (div) {
                        const label = div.closest('label');
                        const radioInput = label.querySelector('input[type="radio"][name="Sort by"]');
                        radioInput.click();
                    }'''
            )
            return await crawler.arun(
                url=f"https://duckduckgo.com/?q={query}+cheap&iax=shopping&ia=shopping",
                config=crawler_config
            )
