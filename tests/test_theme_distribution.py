"""Public blue assets must not contain the private local palette."""
import json,pathlib,tempfile,unittest
from unittest.mock import patch
import theme_assets as theme

class ThemeDistributionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=theme.ROOT/'local-data')
  folder=pathlib.Path(self.tmp.name)
  self.setting=folder/'appearance.json';self.palette=folder/'blue-mint.css'
  self.patches=[patch.object(theme,'SETTING',self.setting),patch.object(theme,'LOCAL_PALETTE',self.palette)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_clean_checkout_defaults_to_blue(self):
  self.assertEqual(theme.preference()['theme'],'blue')
  css=theme.asset('/research-theme.css')[0]
  self.assertNotIn(b'--theme-mint-paper',css)
  self.assertNotIn(b'data-research-theme=green',css)
 def test_local_palette_is_loaded_only_by_local_preference(self):
  self.palette.write_text('/* private palette marker */',encoding='utf-8')
  theme.save({'theme':'blue-mint'})
  self.assertIn(b'private palette marker',theme.asset('/research-theme.css')[0])
  theme.save({'theme':'blue'})
  self.assertNotIn(b'private palette marker',theme.asset('/research-theme.css')[0])
 def test_missing_private_file_falls_back_to_blue(self):
  self.setting.write_text(json.dumps({'theme':'blue-mint'}),encoding='utf-8')
  self.assertEqual(theme.preference()['theme'],'blue')
  self.assertIsNotNone(theme.asset('/research-theme.css'))
 def test_green_option_removed_and_legacy_preference_falls_back(self):
  self.setting.write_text(json.dumps({'theme':'green'}),encoding='utf-8')
  self.assertEqual(theme.preference()['theme'],'blue')
  with self.assertRaises(ValueError):theme.save({'theme':'green'})

if __name__=='__main__':unittest.main()
