import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from openai import OpenAI

from agent.context_guard import ContextLimits, ContextWindowGuard
from agent.generic_agent import GenericAgent
from agent.llm import (
    create_tool_response,
    generation_options,
    items_to_chat,
    resolve_ssl_verification,
    safe_endpoint,
    safe_exception_summary,
)
from agent.messages import normalize_chat_messages
from agent.orchestrator_agent import OrchestratorAgent, create_orchestrator_response


class CompatibilityTests(unittest.TestCase):
    def test_tls_auto_mode_only_bypasses_public_openai(self):
        self.assertFalse(resolve_ssl_verification('https://api.openai.com/v1', 'auto'))
        self.assertTrue(resolve_ssl_verification('https://vllm.internal.example/v1', 'auto'))
        self.assertTrue(resolve_ssl_verification('https://api.openai.com.evil.example/v1', 'auto'))
        self.assertTrue(resolve_ssl_verification('http://vllm:8000/v1', 'auto'))
        self.assertFalse(resolve_ssl_verification('https://vllm.internal/v1', False))
        self.assertEqual(resolve_ssl_verification('https://vllm.internal/v1', '/ca/internal.pem'),
                         '/ca/internal.pem')

    def test_connection_error_summary_includes_root_cause_and_redacts_keys(self):
        try:
            try:
                raise OSError("DNS failed while using sk-secretvalue")
            except OSError as cause:
                raise RuntimeError("Connection error.") from cause
        except RuntimeError as exc:
            summary = safe_exception_summary(exc)

        self.assertIn("RuntimeError: Connection error.", summary)
        self.assertIn("OSError: DNS failed", summary)
        self.assertNotIn("sk-secretvalue", summary)
        self.assertEqual(safe_endpoint("https://user:pass@example.com:8443/v1?q=x"),
                         "https://example.com:8443")

    def test_single_system_message_preserves_tool_protocol(self):
        messages = [{'role': 'system', 'content': 'base'},
                    {'role': 'user', 'content': 'task'},
                    {'role': 'developer', 'content': 'plan'},
                    {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'a'}]},
                    {'role': 'tool', 'tool_call_id': 'a', 'content': 'done'},
                    {'role': 'system', 'content': 'checkpoint'}]
        normalized = normalize_chat_messages(messages, 'role instructions')
        self.assertEqual(normalized[0]['content'], 'role instructions\n\nbase\n\nplan\n\ncheckpoint')
        self.assertEqual([m['role'] for m in normalized], ['system', 'user', 'assistant', 'tool'])
        self.assertEqual(normalized[-1], messages[-2])
        self.assertEqual(len(messages), 6)

    def test_orchestrator_sends_one_system_even_during_context_retry(self):
        agent = OrchestratorAgent.__new__(OrchestratorAgent)
        agent.context_limits = ContextLimits()
        agent.context_guard = ContextWindowGuard(agent.context_limits)
        agent.system_message = 'orchestrator role'
        agent.response_model = create_orchestrator_response(['PLANNER'])
        agent.model, agent.temperature, agent.name = 'qwen', 1.0, 'ORCHESTRATOR'
        agent.llm_options = {}
        requests = []
        def handler(request):
            body = json.loads(request.content)
            requests.append(body)
            self.assertEqual(request.url.path, '/v1/chat/completions')
            self.assertEqual([i for i,m in enumerate(body['messages']) if m['role']=='system'], [0])
            self.assertIn('active plan', body['messages'][0]['content'])
            self.assertNotIn('reasoning_effort', body)
            if len(requests) == 1:
                return httpx.Response(400, json={'error': {'message': 'maximum context length exceeded', 'type': 'BadRequestError'}})
            return self.reply({'role':'assistant','content':json.dumps({'action':'finish','description':'done','agent_name':None})})
        with OpenAI(api_key='test', base_url='http://test/v1', http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
            agent.client = client
            decision = agent.chat_structured([{'role':'user','content':'start'}, {'role':'system','content':'active plan'}])
        self.assertEqual(decision.action, 'finish')
        self.assertEqual(len(requests), 2)

    @staticmethod
    def reply(message, finish_reason='stop'):
        return httpx.Response(200, json={'id':'chat-test','object':'chat.completion','created':1,'model':'qwen',
                                        'choices':[{'index':0,'message':message,'finish_reason':finish_reason}]})

    def test_vllm_worker_roundtrip_retains_reasoning_and_multiple_call_ids(self):
        requests = []
        def handler(request):
            body = json.loads(request.content)
            requests.append(body)
            self.assertEqual(request.url.path, '/v1/chat/completions')
            self.assertEqual([i for i,m in enumerate(body['messages']) if m['role']=='system'], [0])
            self.assertNotIn('reasoning_effort', body)
            self.assertNotIn('store', body)
            if len(requests) == 1:
                return self.reply({'role':'assistant','content':None,'reasoning_content':'Need both results.',
                                   'tool_calls':[{'id':i,'type':'function','function':{'name':'test_tool','arguments':'{}'}} for i in ['a','b']]}, 'tool_calls')
            history = body['messages']
            self.assertEqual(history[-3]['reasoning_content'], 'Need both results.')
            self.assertEqual([m['tool_call_id'] for m in history if m['role']=='tool'], ['a','b'])
            self.assertEqual(len(history[-3]['tool_calls']), 2)
            return self.reply({'role':'assistant','content':'done'})
        with tempfile.TemporaryDirectory() as workspace:
            agent = GenericAgent.__new__(GenericAgent)
            agent.workspace_path, agent.system_message, agent.name = workspace, 'worker', 'TEST'
            agent.context_limits = ContextLimits()
            agent.context_guard = ContextWindowGuard(agent.context_limits)
            agent.model, agent.temperature, agent.llm_options = 'qwen', 1.0, {}
            session = SimpleNamespace(id='test', add_message=lambda message: None)
            with OpenAI(api_key='test', base_url='http://test/v1', http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
                agent.client = client
                with patch('agent.generic_agent.execute_registered_tool', return_value={'ok':True,'output':'ok'}):
                    self.assertEqual(agent.chat([{'role':'user','content':'use tools'}], session), 'done')
        self.assertEqual(len(requests), 2)

    def test_optional_generation_parameters_are_explicit(self):
        self.assertEqual(generation_options({}, None), {})
        self.assertEqual(generation_options({'reasoning_effort':'medium'}, None), {'reasoning_effort':'medium'})
        self.assertEqual(generation_options({'reasoning_effort':'medium'}, None, responses=True), {'reasoning':{'effort':'medium'}})

    def test_invalid_mode_fails_before_http(self):
        with self.assertRaises(ValueError):
            create_tool_response(None, model='test', instructions='', input=[], tools=[], options={'api_mode':'typo'}, temperature=None)
