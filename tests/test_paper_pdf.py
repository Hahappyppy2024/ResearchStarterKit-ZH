import unittest
from unittest.mock import patch
import paper_pdf

class OriginalPdfTests(unittest.TestCase):
    def test_arxiv_abs_and_version_are_normalized(self):
        self.assertEqual(paper_pdf.original_url({'source':'https://arxiv.org/abs/1706.03762v7'}),'https://arxiv.org/pdf/1706.03762v7')
    def test_untrusted_or_local_urls_are_rejected(self):
        for url in ['http://127.0.0.1/a.pdf','https://evil.example/a.pdf','https://arxiv.org.evil.example/a.pdf','https://user:pass@arxiv.org/pdf/1706.03762','https://arxiv.org:444/pdf/1706.03762','https://arxiv.org/pdf/../../file']:
            with self.subTest(url=url),self.assertRaises(ValueError):paper_pdf.original_url({'pdf':url})
    def test_cache_is_based_on_url_not_user_path(self):
        a=paper_pdf.cache_path({'source':'https://arxiv.org/abs/1706.03762'})
        b=paper_pdf.cache_path({'pdf':'https://arxiv.org/pdf/1706.03762'})
        self.assertEqual(a,b)
        self.assertEqual(a.parent,paper_pdf.CACHE)
        self.assertEqual(len(a.stem),64)
    def test_official_html_is_not_passed_off_as_a_pdf(self):
        with self.assertRaises(ValueError):paper_pdf.original_url({'source':'https://papers.nips.cc/paper/1234'})

if __name__=='__main__':unittest.main()
