import contextlib,unittest
from unittest.mock import patch
import daily_paper_statistics as stats

class DailyPaperStatisticsTest(unittest.TestCase):
    def test_first_task_starts_reading_without_completing_paper(self):
        rows=[{'id':'started','startedDate':'2026-10-27','tasks':{'methodology':{'done':True}}},
              {'id':'other-task','tasks':{'problem':{'done':True}}},
              {'id':'historical','tasks':{'methodology':{'done':True}}},
              {'id':'cancelled','startedDate':'2026-10-27','tasks':{'methodology':{'done':False}}}]
        with patch.object(stats.study,'connection',return_value=contextlib.nullcontext(None)),patch.object(stats.study,'records',side_effect=lambda c,kind:rows if kind=='paper-knowledge' else []):
            result=stats.snapshot('2026-10-27')
        self.assertEqual(result['started'],1)
        self.assertEqual(result['inProgress'],2)
        self.assertEqual(result['today'],0)
        self.assertEqual(result['total'],0)

if __name__=='__main__':unittest.main()
