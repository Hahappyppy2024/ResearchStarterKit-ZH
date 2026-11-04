import pathlib,tempfile,unittest,zipfile
import learning_editor as e
class EditorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent/'local-data');self.source=pathlib.Path(self.tmp.name)/'source.pptx'
  slide=f'''<p:sld xmlns:p="{e.P}" xmlns:a="{e.A}" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" mc:Ignorable="p14"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/></p:nvSpPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr algn="l"/><a:r><a:rPr sz="2400" b="1"/><a:t>Original title</a:t></a:r><a:endParaRPr lang="zh-CN"/></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'''
  with zipfile.ZipFile(self.source,'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr('ppt/slides/slide1.xml',slide.replace('Original title','First file'))
   z.writestr('ppt/slides/slide2.xml',slide)
   z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{e.P}" xmlns:r="{e.R}"><p:sldIdLst><p:sldId id="2" r:id="s2"/><p:sldId id="1" r:id="s1"/></p:sldIdLst></p:presentation>')
   z.writestr('ppt/_rels/presentation.xml.rels','<Relationships><Relationship Id="s1" Target="slides/slide1.xml"/><Relationship Id="s2" Target="slides/slide2.xml"/></Relationships>')
   z.writestr('ppt/media/image1.png',b'image bytes unchanged')
  self.original=self.source.read_bytes()
 def tearDown(self):self.tmp.cleanup()
 def test_edit_preserves_parts_styles_and_undo(self):
  slide=e.get_slide(self.source,0);self.assertEqual(slide['fields'][0]['text'],'Original title')
  e.save_slide(self.source,0,slide['revision'],[{'id':'2','text':'新标题 & <example>\n第二段'}])
  self.assertEqual(e.get_slide(self.source,0)['fields'][0]['text'],'新标题 & <example>\n第二段')
  with zipfile.ZipFile(self.source) as z:
   self.assertEqual(z.read('ppt/media/image1.png'),b'image bytes unchanged')
   self.assertIn(b'First file',z.read('ppt/slides/slide1.xml'))
   self.assertIn(b'sz="2400"',z.read('ppt/slides/slide2.xml'));self.assertIn(b'xmlns:p14=',z.read('ppt/slides/slide2.xml'))
  with self.assertRaises(ValueError):e.save_slide(self.source,0,slide['revision'],[])
  e.undo(self.source,e.get_slide(self.source,0)['revision']);self.assertEqual(self.source.read_bytes(),self.original)
 def test_invalid_shape_and_xml_characters(self):
  state=e.get_slide(self.source,0)
  for field in [{'id':'missing','text':'bad'},{'id':'2','text':'bad\x00text'}]:
   with self.assertRaises(ValueError):e.save_slide(self.source,0,state['revision'],[field])
  self.assertEqual(self.source.read_bytes(),self.original)
if __name__=='__main__':unittest.main()
