"""Real worker execution and full-topic persistence: issues #18 and #21.

Run: WECODE_DISPOSABLE_E2E=yes python -m unittest e2e.runtime_acceptance -v
"""
from e2e import test_browser as core
from playwright.sync_api import expect
import re


class RuntimeAcceptance(core.BrowserTests):
    for _name in list(vars(core.BrowserTests)):
        if _name.startswith('test_'):
            locals()[_name] = None

    def editor_language(self, language):
        self.page.get_by_role('group', name='Editor language', exact=True).get_by_role(
            'button', name=language, exact=True).click()

    def code(self, source):
        self.page.locator('.cm-content').fill(source)

    def submit(self, outcome):
        self.page.get_by_role('button', name=re.compile('^Submit')).click()
        expect(self.page.locator('.submission-summary h1')).to_have_text(outcome, timeout=130000)
        expect(self.page.get_by_role('button', name=re.compile('^Submit'))).to_be_enabled()

    def exercise_execution(self, language, correct, wrong, error):
        self.signed_in()
        self.open_problem(61 if language == 'SQL' else 1)
        self.editor_language(language)
        self.code(correct)
        self.page.get_by_role('button', name=re.compile('Run$')).click()
        expect(self.page.locator('.code-result-summary h3')).to_have_text('Examples passed', timeout=130000)
        self.submit('Accepted')
        report = self.page.locator('.submission-summary')
        progress = report.get_by_role('progressbar', name='Test cases passed', exact=True)
        self.assertGreater(int(progress.get_attribute('aria-valuemax')), 1)
        self.assertEqual(progress.get_attribute('aria-valuenow'), progress.get_attribute('aria-valuemax'))
        expect(report.locator('.submission-metrics')).to_contain_text('ms')
        report.locator('summary').filter(has_text='Submitted code').click()
        expect(report.locator('.submission-source pre')).to_have_text(correct)
        self.page.get_by_role('button', name=re.compile('Testcase$')).click()
        expect(self.page.locator('.code-test-tabs button').first).to_be_visible()
        self.page.get_by_role('button', name=re.compile('Test Result$')).click()
        self.code(wrong)
        self.submit('Wrong answer')
        self.code(error)
        if language == 'Java':
            self.page.get_by_role('button', name=re.compile('^Submit')).click()
            expect(self.page.locator('.code-feedback [role=alert]')).not_to_be_empty(timeout=130000)
        else:
            self.submit('Runtime error')
            self.page.locator('summary').filter(has_text='Runtime error details').click()
            expect(self.page.locator('.code-runtime-error pre')).not_to_be_empty()

    def test_execution_python(self):
        correct = 'def solve(values):\n    return sum(x for x in values if x > 0)\n'
        self.exercise_execution('Python', correct, 'def solve(values):\n    return 0\n',
                                'def solve(values):\n    raise ValueError("E2E failure")\n')
        self.code('def solve(values):\n    while True:\n        pass\n')
        self.page.get_by_role('button', name=re.compile('Run$')).click()
        expect(self.page.locator('.code-feedback-heading span')).to_have_text('Running tests…', timeout=130000)
        self.page.get_by_role('button', name='Stop', exact=True).click()
        expect(self.page.locator('.code-feedback-heading span')).to_have_text('Cancelled')
        self.code(correct)
        self.submit('Accepted')

    def test_execution_java(self):
        self.exercise_execution('Java',
            'public class Solution { public static Object solve(int[] values) { int total=0; for(int x:values) if(x>0) total+=x; return total; } }',
            'public class Solution { public static Object solve(int[] values) { return 0; } }',
            'public class Solution { this is not valid Java; }')

    def test_execution_sql(self):
        self.exercise_execution('SQL', 'SELECT id,name FROM members ORDER BY name,id;',
            'SELECT id,name FROM members WHERE false ORDER BY name,id;', 'SELEC invalid;')

    def completed_topic(self, language):
        self.signed_in()
        self.nav('Learning way')
        self.page.get_by_role('group', name='Learning language', exact=True).get_by_role(
            'button', name=re.compile('^'+language)).click()
        route=self.page.locator('.lw-route-topic').first
        expect(route).to_be_enabled()
        title=route.locator('strong').inner_text()
        route.click()
        with self.page.expect_response(lambda r: '/api/rest/v1/learning_way_progress' in r.url and r.request.method == 'POST') as saved:
            self.page.get_by_role('button', name=re.compile('I have read the notes')).click()
        self.assertTrue(saved.value.ok)
        expressions=[('a, b','a + b'), ('width, height','2 * (width + height)'),
                     ('minutes, seconds','minutes * 60 + seconds'), ('sweets, people','sweets % people'),
                     ('price, quantity, delivery','price * quantity + delivery')]
        sql=['SELECT id,title FROM courses ORDER BY id;', 'SELECT id,name FROM members ORDER BY id;',
             'SELECT id,language FROM courses ORDER BY id;', 'SELECT id,fee AS course_fee FROM courses ORDER BY id;',
             'SELECT id,fee * 12 AS annual_fee FROM courses ORDER BY id;']
        for index,(parameters,expression) in enumerate(expressions):
            self.page.locator('.lw-task-list > button').nth(index).click()
            expect(self.page.get_by_role('group', name='Editor language', exact=True).get_by_role(
                'button', name=language, exact=True)).to_have_attribute('aria-pressed', 'true')
            if language == 'Python':
                source=f'def solve({parameters}):\n    return {expression}\n'
            elif language == 'Java':
                args=', '.join('int '+p.strip() for p in parameters.split(','))
                source=f'public class Solution {{ public static Object solve({args}) {{ return {expression}; }} }}'
            else:
                source=sql[index]
            self.code(source)
            with self.page.expect_response(lambda r: '/api/rest/v1/learning_way_progress' in r.url and r.request.method == 'POST', timeout=130000) as saved:
                self.page.get_by_role('button', name=re.compile('^Submit')).click()
            self.assertTrue(saved.value.ok)
            expect(self.page.locator('.lw-task-accepted')).to_contain_text('Exercise completed', timeout=130000)
            self.page.get_by_role('button', name=re.compile('Continue this topic')).click()
        expect(self.page.locator('.lw-topic-complete')).to_contain_text('Topic completed')
        self.page.get_by_role('button', name=re.compile('Next topic')).click()
        expect(self.page.locator('#learning-way-heading')).not_to_have_text(title)
        self.new_context()
        self.login()
        self.nav('Learning way')
        self.page.get_by_role('group', name='Learning language', exact=True).get_by_role(
            'button', name=re.compile('^'+language)).click()
        first=self.page.locator('.lw-route-topic').first
        expect(first).to_have_class(re.compile('is-done'))
        expect(first).to_contain_text('5/5 exercises completed')
        expect(first.get_by_label('Completed', exact=True)).to_be_visible()

    def test_topic_python(self):
        self.completed_topic('Python')

    def test_topic_java(self):
        self.completed_topic('Java')

    def test_topic_sql(self):
        self.completed_topic('SQL')
