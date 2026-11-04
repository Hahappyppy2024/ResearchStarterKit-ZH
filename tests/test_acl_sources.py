import unittest
from conference_sources import parse_acl_bib

class AclSourceTests(unittest.TestCase):
    def bib(self,title='"A {B}enchmark"',year='2025',path='2025.acl-long.1'):
        return '@inproceedings{example,\n    title = '+title+',\n    author = "Doe, Jane  and Smith, John",\n    year = "'+year+'",\n    url = "https://aclanthology.org/'+path+'/",\n    doi = "10.1/example"\n}\n'
    def test_metadata_track_and_braced_titles(self):
        row=parse_acl_bib(self.bib('{A {B}enchmark}'),2025,'long')[0]
        self.assertEqual(row['title'],'A Benchmark')
        self.assertEqual(row['authors'],'Jane Doe; John Smith')
        self.assertEqual(row['track'],'Long Papers')
        self.assertEqual(row['pdf'],'https://aclanthology.org/2025.acl-long.1.pdf')
    def test_reject_wrong_year_or_volume(self):
        with self.assertRaises(ValueError):parse_acl_bib(self.bib(year='2026'),2025,'long')
        with self.assertRaises(ValueError):parse_acl_bib(self.bib(path='2025.findings-acl.1'),2025,'long')
    def test_skip_volume_front_matter(self):
        with self.assertRaises(ValueError):parse_acl_bib('@proceedings{front,\n title = "Volume"\n}',2025,'long')

if __name__=='__main__':unittest.main()
