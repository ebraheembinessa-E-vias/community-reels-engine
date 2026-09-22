import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reelkit.core import (approval_valid, digest, map_captions, save,
                          validate_captions, validate_plan)
from reelkit.composition import STYLES, build, caption_html
from reelkit import gemini
from reelkit.story import prepare_story


class EditSafety(unittest.TestCase):
    def test_rejects_overlap_backwards_and_nonfinite_cuts(self):
        cases=[[(0,2),(1,3)],[(2,1)],[(0,math.inf)],[(0,math.nan)],[(-1,1)],[(0,11)]]
        for spans in cases:
            with self.subTest(spans=spans),self.assertRaises(ValueError):
                validate_plan({"keep":[{"start":a,"end":b} for a,b in spans]},10)

    def test_frame_alignment_keeps_word_tail(self):
        result=validate_plan({"keep":[{"start":.11,"end":1.011}]},5)[0]
        self.assertLessEqual(result['start'],.11)
        self.assertGreaterEqual(result['end'],1.011)

    def test_crossed_phrase_is_flagged_not_falsely_captioned(self):
        caps,questions=map_captions([{"start":1,"end":4,"text":"A complete phrase"}], [{"start":2,"end":4}])
        self.assertEqual(caps,[])
        self.assertEqual(len(questions),1)

    def test_caption_remapping_across_removed_gap(self):
        caps,questions=map_captions([{"start":.2,"end":1,"text":"Opening"},{"start":5,"end":6,"text":"Ending"}], [{"start":0,"end":2},{"start":4,"end":7}])
        self.assertEqual(caps[1]['start'],3)
        self.assertEqual(caps[1]['end'],4)
        self.assertEqual(questions,[])

    def test_changed_clean_file_invalidates_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for f in ['clean.mp4','captions.json','plan.json']:(p/f).write_text('original')
            save(p/'approval.json',{'sha256':{f:digest(p/f) for f in ['clean.mp4','captions.json','plan.json']}})
            approval_valid(p)
            (p/'clean.mp4').write_text('new cut')
            with self.assertRaises(ValueError):approval_valid(p)

    def test_invalid_captions_stop_the_visual_pass(self):
        for captions in [[{'start':0,'end':3,'text':'A'},{'start':2,'end':4,'text':'B'}],
                         [{'start':0,'end':9,'text':'Outside'}], [{'start':0,'end':1,'text':'x'*111}]]:
            with self.assertRaises(ValueError):validate_captions(captions,8)

    def test_caption_text_is_not_executable_markup(self):
        text=caption_html('\u0645\u062b\u0627\u0644 <script>alert(1)</script> Codex')
        self.assertNotIn('<script>',text)
        self.assertIn('&lt;',text)
        self.assertIn('<bdi dir="ltr" data-layout-allow-overlap="true">',text)


class StorySafety(unittest.TestCase):
    def fixture(self,p):
        data={'audience':'Test fixture','script':'A complete thought.','script_approved_by':'Synthetic test',
              'duration':5,'captions':[{'start':0,'end':5,'text':'A complete thought.'}],
              'elements':[{'start':0,'end':5,'kind':'statement','title':'One thought'}]}
        save(p/'story.json',data)
        return data

    def test_story_cannot_invent_script_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);data=self.fixture(p);data.pop('script_approved_by');save(p/'story.json',data)
            with patch('reelkit.story.project',return_value=p/'output'),patch('reelkit.story.ffmpeg') as render:
                with self.assertRaisesRegex(ValueError,'actual approval'):prepare_story(p/'story.json','test',silent=True)
                render.assert_not_called();self.assertFalse((p/'output').exists())

    def test_story_requires_explicit_sound_choice(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.fixture(p)
            with patch('reelkit.story.project',return_value=p/'output'):
                with self.assertRaisesRegex(ValueError,'deliberate'):prepare_story(p/'story.json','test')

    def test_narration_needs_measured_timing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.fixture(p)
            with patch('reelkit.story.project',return_value=p/'output'),patch('reelkit.story.ffmpeg') as render:
                with self.assertRaisesRegex(ValueError,'measure caption timing'):prepare_story(p/'story.json','test',p/'voice.wav')
                render.assert_not_called()

    def test_wrong_narration_duration_stops_before_render(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);data=self.fixture(p);data.update(timing_verified=True,timing_verified_by='Test editor');save(p/'story.json',data)
            with patch('reelkit.story.project',return_value=p/'output'),patch('reelkit.story.probe',return_value={'streams':[{'codec_type':'audio'}]}),patch('reelkit.story.duration',return_value=8),patch('reelkit.story.ffmpeg') as render:
                with self.assertRaisesRegex(ValueError,'differs from the narration'):prepare_story(p/'story.json','test',p/'voice.wav')
                render.assert_not_called();self.assertFalse((p/'output').exists())


class ProviderSafety(unittest.TestCase):
    def test_wrapped_provider_object_is_saved_and_recovered(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);media=p/'proxy.mp4';media.write_bytes(b'synthetic-test')
            reply={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'[{"coverage":{"complete":true}}]'}]}}],
                   'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20}}
            def network(key,method,url,*args,**kwargs):
                if 'upload/v1beta' in url:return {'X-Goog-Upload-URL':gemini.API+'/upload/test'},b'{}'
                if '/upload/test' in url:return {},json.dumps({'file':{'name':'files/test','state':'ACTIVE','uri':gemini.API+'/v1beta/files/test'}}).encode()
                return {},b'{}'
            with patch.object(gemini,'config',return_value=('fake-test-key','gemini-3.8-flash')),patch.object(gemini,'request',side_effect=network),patch.object(gemini,'json_request',side_effect=[{'totalTokens':100},reply]):
                result=gemini.analyze(media,'test prompt',p/'usage.json',allow_upload=True)
            self.assertTrue(result['coverage']['complete'])
            self.assertTrue((p/'provider-responses/response-001.json').exists())
            self.assertEqual(json.loads((p/'usage.json').read_text())['calls'][0]['state'],'complete')

    def test_no_upload_without_explicit_flag(self):
        with tempfile.TemporaryDirectory() as d,patch.object(gemini,'request') as network:
            with self.assertRaises(ValueError):gemini.analyze(Path(d)/'private.mp4','prompt',Path(d)/'usage.json')
            network.assert_not_called()
            self.assertFalse((Path(d)/'usage.lock').exists())

    def test_key_cannot_be_sent_to_other_host(self):
        with self.assertRaises(ValueError):gemini.request('fake-test-key','POST','https://example.com/collect')

    def test_concurrent_request_cannot_reserve_same_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'usage.lock').write_text('busy')
            with patch.object(gemini,'request') as network,self.assertRaises(ValueError):
                gemini.analyze(p/'private.mp4','prompt',p/'usage.json',allow_upload=True)
            network.assert_not_called()
            self.assertTrue((p/'usage.lock').exists())

    def test_unknown_model_fails_before_network(self):
        with patch.dict('os.environ',{'GEMINI_API_KEY':'fake-test-key','GEMINI_MODEL':'unpriced-model'}):
            with self.assertRaises(ValueError):gemini.config()


if __name__=='__main__':unittest.main()


class PulseStyle(unittest.TestCase):
    """The fourth style: a faceless series where a signal travels through the steps (added 2026-09-22)."""

    def test_pulse_flow_becomes_a_graph_with_links_and_a_signal(self):
        import subprocess
        from reelkit.core import ROOT
        self.assertIn('pulse', STYLES)
        with tempfile.TemporaryDirectory(dir=ROOT / 'projects') as d:
            p = Path(d)
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:r=30:d=1',
                            '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', str(p / 'clean.mp4')], check=True)
            save(p / 'plan.json', {'fixture': True, 'keep': [{'start': 0, 'end': 1}]})
            save(p / 'captions.json', [{'start': 0.1, 'end': 0.9, 'text': 'A step.', 'direction': 'ltr'}])
            save(p / 'elements.json', [{'start': 0.1, 'end': 0.95, 'kind': 'flow', 'label': 'TEST', 'title': 'Three steps', 'items': ['One', 'Two', 'Three']}])
            save(p / 'approval.json', {'by': 'synthetic test', 'sha256': {n: digest(p / n) for n in ('clean.mp4', 'captions.json', 'plan.json')}})
            out = build(p, 'pulse', True)
            html_text = (out / 'index.html').read_text(encoding='utf-8')
            self.assertEqual(html_text.count('class="gnode"'), 3)
            self.assertEqual(html_text.count('class="glink"'), 2)
            self.assertIn('class="gdot" data-layout-allow-occlusion="true"', html_text)
            self.assertIn('pulseGraph', html_text)
            self.assertIn('"style": "pulse"', html_text)


class PortableTools(unittest.TestCase):
    def test_hdr_proxy_has_a_road_without_zscale(self):
        from reelkit.core import video_filter
        info = {"streams": [{"codec_type": "video", "color_transfer": "arib-std-b67"}]}
        with_z = video_filter(info, 360, 640, zscale=True)
        without = video_filter(info, 360, 640, zscale=False)
        self.assertIn("zscale", with_z)
        self.assertNotIn("zscale", without)
        self.assertIn("colorspace=all=bt709", without)
        self.assertTrue(without.endswith("format=yuv420p"))


class FirstRealRunLessons(unittest.TestCase):
    def test_minutes_written_as_hundreds_become_seconds(self):
        from reelkit.core import normalize_times
        r = normalize_times({"segments": [{"start": 57.5, "end": 59.0, "text": "a"}, {"start": 100.0, "end": 103.0, "text": "b"}],
                             "keep": [{"start": 211.0, "end": 217.0}], "coverage": {"watched_to_seconds": 138.3}}, 138.3)
        self.assertEqual(r["segments"][0]["start"], 57.5)
        self.assertEqual(r["segments"][1]["start"], 60.0)
        self.assertEqual(r["keep"][0]["end"], 137.0)
        self.assertEqual(r["coverage"]["watched_to_seconds"], 138.3)

    def test_product_words_return_to_latin(self):
        from reelkit.core import latinize
        ar = "\u062a\u0631\u0648\u062d \u0644\u062c\u0648\u062c\u0644 \u0633\u062a\u0648\u062f\u064a\u0648 \u0648\u062a\u0627\u062e\u0630 \u0627\u064a \u0628\u064a \u0627\u0627\u064a \u0643\u064a\u0632"
        out = latinize(ar)
        self.assertIn("Google Studio", out)
        self.assertIn("API keys", out)
        self.assertNotIn("\u062c\u0648\u062c\u0644", out)
