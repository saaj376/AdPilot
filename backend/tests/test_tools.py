from tools.scraper_tools import _extract_text, _fallback_competitors


def test_extract_text_removes_non_content_tags():
		html = """
		<html>
			<body>
				<header>Header content</header>
				<nav>Nav links</nav>
				<script>console.log('hidden')</script>
				<main>Visible content for users.</main>
				<footer>Footer details</footer>
			</body>
		</html>
		"""

		text = _extract_text(html)

		assert "Visible content for users." in text
		assert "Header content" not in text
		assert "Nav links" not in text
		assert "Footer details" not in text
		assert "hidden" not in text


def test_extract_text_respects_max_chars():
		html = "<html><body><main>" + ("abc " * 5000) + "</main></body></html>"

		text = _extract_text(html, max_chars=200)

		assert len(text) == 200


def test_fallback_competitors_shape():
		competitors = _fallback_competitors("pizza restaurant", "Austin, TX")

		assert len(competitors) == 3
		for item in competitors:
				assert "name" in item
				assert "snippet" in item
				assert "scraped_text" in item
