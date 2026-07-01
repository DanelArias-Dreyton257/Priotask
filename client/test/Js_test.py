"""
Playwright-driven unit tests for the client JS modules (views.js, api.js).

Each test loads the app shell in a headless Chromium browser and exercises
JS functions in-browser via page.evaluate() with dynamic ES module imports.
This lets us test the real browser behaviour (DOM, classList, etc.) without
a JS build step or a separate test runner.

The Flask client is started on an ephemeral port before the test suite and
torn down afterwards.  API calls that would normally hit the server are
intercepted by page.route() so the tests are self-contained.

Run alongside the other tests:
    python -m unittest discover -s client/test -p "*_test.py"
Or in isolation:
    python -m unittest client.test.Js_test
"""

import json
import threading
import unittest
from datetime import date

from werkzeug.serving import make_server

from client.src.Client import create_app

# Port for the test Flask instance — kept well away from 5500 (the real client).
_TEST_PORT = 15500
_BASE_URL = f"http://127.0.0.1:{_TEST_PORT}"


# ---------------------------------------------------------------------------
# Test server lifecycle helpers
# ---------------------------------------------------------------------------

def _start_test_server():
    """Start the Flask client app on _TEST_PORT in a daemon thread."""
    app = create_app("http://localhost:5000")
    server = make_server("127.0.0.1", _TEST_PORT, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------------------------------------------------------------------------
# Playwright availability guard
# ---------------------------------------------------------------------------

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Base class shared by all Playwright test classes
# ---------------------------------------------------------------------------

@unittest.skipUnless(_PLAYWRIGHT_AVAILABLE, "playwright not installed — run: python -m playwright install chromium")
class _PlaywrightBase(unittest.TestCase):
    """Shared Chromium browser + Flask server lifecycle for JS tests."""

    _http_server = None
    _playwright = None
    _browser = None

    @classmethod
    def setUpClass(cls):
        cls._http_server = _start_test_server()
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        if cls._browser:
            cls._browser.close()
        if cls._playwright:
            cls._playwright.stop()
        if cls._http_server:
            cls._http_server.shutdown()

    def setUp(self):
        self.page = self._browser.new_page()
        self.page.goto(_BASE_URL)
        # Wait until app.js has finished its initial setup (auth-section is
        # present whether or not a session exists in localStorage).
        self.page.wait_for_selector("#auth-section")

    def tearDown(self):
        self.page.close()

    def js(self, script):
        """Shorthand: evaluate script in the page context."""
        return self.page.evaluate(script)


# ---------------------------------------------------------------------------
# views.js — spinner / loading-state helpers (Phase 12)
# ---------------------------------------------------------------------------

class SpinnerViewsTest(_PlaywrightBase):

    def test_show_today_plan_loading_inserts_spinner_into_plan_list(self):
        html = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.showTodayPlanLoading();
            return document.getElementById('plan-list').innerHTML;
        }""")
        self.assertIn('spinner', html)
        self.assertIn('Loading', html)

    def test_show_week_plan_loading_inserts_spinner_into_week_grid(self):
        html = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.showWeekPlanLoading();
            return document.getElementById('week-grid').innerHTML;
        }""")
        self.assertIn('spinner', html)
        self.assertIn('Loading', html)

    def test_set_train_button_loading_true_disables_and_shows_spinner(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.setTrainButtonLoading(true);
            const btn = document.getElementById('train-button');
            return { disabled: btn.disabled, hasSpinner: btn.innerHTML.includes('spinner') };
        }""")
        self.assertTrue(result['disabled'])
        self.assertTrue(result['hasSpinner'])

    def test_set_train_button_loading_false_re_enables_button(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.setTrainButtonLoading(true);
            Views.setTrainButtonLoading(false);
            const btn = document.getElementById('train-button');
            return { disabled: btn.disabled, text: btn.textContent };
        }""")
        self.assertFalse(result['disabled'])
        self.assertIn('Train', result['text'])


# ---------------------------------------------------------------------------
# views.js — message banner
# ---------------------------------------------------------------------------

class MessageViewsTest(_PlaywrightBase):

    def test_show_message_error_applies_error_class_and_reveals_banner(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.showMessage('Something went wrong', true);
            const el = document.getElementById('message-banner');
            return {
                text: el.textContent,
                isError: el.classList.contains('error'),
                hidden: el.classList.contains('hidden')
            };
        }""")
        self.assertEqual(result['text'], 'Something went wrong')
        self.assertTrue(result['isError'])
        self.assertFalse(result['hidden'])

    def test_show_message_info_applies_info_class(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.showMessage('All good', false);
            const el = document.getElementById('message-banner');
            return { isInfo: el.classList.contains('info'), isError: el.classList.contains('error') };
        }""")
        self.assertTrue(result['isInfo'])
        self.assertFalse(result['isError'])

    def test_clear_message_hides_the_banner(self):
        hidden = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.showMessage('temp', false);
            Views.clearMessage();
            return document.getElementById('message-banner').classList.contains('hidden');
        }""")
        self.assertTrue(hidden)


# ---------------------------------------------------------------------------
# views.js — category field (wireCategoryField / readCategoryField)
# ---------------------------------------------------------------------------

class CategoryFieldViewsTest(_PlaywrightBase):

    def test_wire_known_value_selects_it_in_dropdown(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            const inp = document.createElement('input');
            Views.wireCategoryField(sel, inp, ['work', 'personal'], 'work');
            return { value: sel.value, inputHidden: inp.classList.contains('hidden') };
        }""")
        self.assertEqual(result['value'], 'work')
        self.assertTrue(result['inputHidden'])

    def test_wire_unknown_value_shows_new_input_prefilled(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            const inp = document.createElement('input');
            Views.wireCategoryField(sel, inp, ['work', 'personal'], 'study');
            return { selectValue: sel.value, inputValue: inp.value, inputHidden: inp.classList.contains('hidden') };
        }""")
        self.assertEqual(result['selectValue'], '__new__')
        self.assertEqual(result['inputValue'], 'study')
        self.assertFalse(result['inputHidden'])

    def test_wire_empty_value_selects_none_option(self):
        value = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            const inp = document.createElement('input');
            Views.wireCategoryField(sel, inp, ['work'], '');
            return sel.value;
        }""")
        self.assertEqual(value, '')

    def test_wire_adds_add_new_option_at_end(self):
        count = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            const inp = document.createElement('input');
            Views.wireCategoryField(sel, inp, ['a', 'b'], '');
            // options: (none), a, b, + Add new...
            return sel.options.length;
        }""")
        self.assertEqual(count, 4)

    def test_read_returns_selected_known_category(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            const inp = document.createElement('input');
            Views.wireCategoryField(sel, inp, ['work', 'personal'], 'personal');
            return Views.readCategoryField(sel, inp);
        }""")
        self.assertEqual(result, 'personal')

    def test_read_returns_new_text_when_new_option_chosen(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            const inp = document.createElement('input');
            Views.wireCategoryField(sel, inp, ['work'], 'hobby');
            return Views.readCategoryField(sel, inp);
        }""")
        self.assertEqual(result, 'hobby')

    def test_read_returns_empty_string_when_none_selected(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            const inp = document.createElement('input');
            Views.wireCategoryField(sel, inp, ['work'], '');
            return Views.readCategoryField(sel, inp);
        }""")
        self.assertEqual(result, '')


# ---------------------------------------------------------------------------
# views.js — recurrence field (wireRecurrenceField / readRecurrenceField)
# ---------------------------------------------------------------------------

class RecurrenceFieldViewsTest(_PlaywrightBase):

    _RECURRENCE_SETUP = """
        const sel = document.createElement('select');
        sel.innerHTML = '<option value="">none</option>'
            + '<option value="day">Daily</option>'
            + '<option value="week">Weekly</option>'
            + '<option value="month">Monthly</option>';
        const interval = document.createElement('input');
        interval.type = 'number';
        const end = document.createElement('input');
        end.type = 'date';
    """

    def test_no_recurrence_hides_interval_and_end_inputs(self):
        result = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            {self._RECURRENCE_SETUP}
            Views.wireRecurrenceField(sel, interval, end, {{}});
            return {{ intervalHidden: interval.classList.contains('hidden'), endHidden: end.classList.contains('hidden') }};
        }}""")
        self.assertTrue(result['intervalHidden'])
        self.assertTrue(result['endHidden'])

    def test_with_recurrence_unit_reveals_interval_and_end(self):
        result = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            {self._RECURRENCE_SETUP}
            Views.wireRecurrenceField(sel, interval, end, {{ recurrence_unit: 'week', recurrence_interval: 2 }});
            return {{
                intervalHidden: interval.classList.contains('hidden'),
                endHidden: end.classList.contains('hidden'),
                intervalValue: interval.value,
                selectValue: sel.value
            }};
        }}""")
        self.assertFalse(result['intervalHidden'])
        self.assertFalse(result['endHidden'])
        self.assertEqual(result['intervalValue'], '2')
        self.assertEqual(result['selectValue'], 'week')

    def test_read_no_recurrence_returns_null_unit_and_interval(self):
        result = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            {self._RECURRENCE_SETUP}
            Views.wireRecurrenceField(sel, interval, end, {{}});
            return Views.readRecurrenceField(sel, interval, end);
        }}""")
        self.assertIsNone(result['recurrence_unit'])
        self.assertIsNone(result['recurrence_interval'])
        self.assertIsNone(result['recurrence_end_date'])

    def test_read_weekly_returns_correct_unit_and_interval(self):
        result = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            {self._RECURRENCE_SETUP}
            Views.wireRecurrenceField(sel, interval, end, {{ recurrence_unit: 'month', recurrence_interval: 3 }});
            return Views.readRecurrenceField(sel, interval, end);
        }}""")
        self.assertEqual(result['recurrence_unit'], 'month')
        self.assertEqual(result['recurrence_interval'], 3)

    def test_read_with_end_date_returns_end_date_string(self):
        result = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            {self._RECURRENCE_SETUP}
            Views.wireRecurrenceField(sel, interval, end, {{
                recurrence_unit: 'day', recurrence_interval: 1, recurrence_end_date: '2026-12-31'
            }});
            return Views.readRecurrenceField(sel, interval, end);
        }}""")
        self.assertEqual(result['recurrence_end_date'], '2026-12-31')


# ---------------------------------------------------------------------------
# views.js — populateFilterSelect
# ---------------------------------------------------------------------------

class PopulateFilterSelectTest(_PlaywrightBase):

    def test_fills_options_with_all_label_first(self):
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            Views.populateFilterSelect(sel, ['alpha', 'beta', 'gamma'], 'All types');
            return { count: sel.options.length, first: sel.options[0].textContent, second: sel.options[1].value };
        }""")
        self.assertEqual(result['count'], 4)   # "All types" + 3 values
        self.assertEqual(result['first'], 'All types')
        self.assertEqual(result['second'], 'alpha')

    def test_preserves_current_selection_across_repopulate(self):
        value = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            Views.populateFilterSelect(sel, ['a', 'b', 'c'], 'All');
            sel.value = 'b';
            Views.populateFilterSelect(sel, ['a', 'b', 'c', 'd'], 'All');
            return sel.value;
        }""")
        self.assertEqual(value, 'b')

    def test_resets_to_all_when_previous_value_disappears(self):
        value = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const sel = document.createElement('select');
            Views.populateFilterSelect(sel, ['a', 'b'], 'All');
            sel.value = 'b';
            Views.populateFilterSelect(sel, ['a', 'c'], 'All');   // 'b' removed
            return sel.value;
        }""")
        self.assertEqual(value, '')


# ---------------------------------------------------------------------------
# views.js — renderPlan
# ---------------------------------------------------------------------------

class RenderPlanViewsTest(_PlaywrightBase):

    def test_renders_task_name_and_hours(self):
        html = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.renderPlan([{
                rank: 1, score: 42.0, recommended_hours_today: 3.0,
                task: { name: 'Write report', deadline: '2099-12-31', done: false, task_id: 1 }
            }]);
            return document.getElementById('plan-list').innerHTML;
        }""")
        self.assertIn('Write report', html)
        self.assertIn('3.0h', html)
        self.assertIn('#1', html)

    def test_empty_plan_shows_placeholder(self):
        html = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.renderPlan([]);
            return document.getElementById('plan-list').innerHTML;
        }""")
        self.assertIn('Nothing scheduled', html)

    def test_task_due_today_renders_badge(self):
        today = date.today().isoformat()
        html = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            Views.renderPlan([{{
                rank: 1, score: 10.0, recommended_hours_today: 1.0,
                task: {{ name: 'Due today task', deadline: '{today}', done: false, task_id: 2 }}
            }}]);
            return document.getElementById('plan-list').innerHTML;
        }}""")
        self.assertIn('due-today-badge', html)
        self.assertIn('due-today', html)

    def test_future_task_has_no_due_today_badge(self):
        html = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.renderPlan([{
                rank: 1, score: 5.0, recommended_hours_today: 2.0,
                task: { name: 'Future task', deadline: '2099-01-01', done: false, task_id: 3 }
            }]);
            return document.getElementById('plan-list').innerHTML;
        }""")
        self.assertNotIn('due-today-badge', html)


# ---------------------------------------------------------------------------
# api.js — ApiError on server error responses
# ---------------------------------------------------------------------------

class ApiClientTest(_PlaywrightBase):

    def test_api_error_raised_on_4xx_response(self):
        self.page.route("**/api/users", lambda route: route.fulfill(
            status=400,
            content_type="application/json",
            body='{"error": "username already taken"}',
        ))
        result = self.js("""async () => {
            const { ApiClient, ApiError } = await import('/static/js/api.js');
            const api = new ApiClient('http://localhost:5000');
            try {
                await api.register('x', 'y', 'z@z.com');
                return { threw: false };
            } catch (e) {
                return { threw: true, isApiError: e instanceof ApiError, status: e.status, message: e.message };
            }
        }""")
        self.assertTrue(result['threw'])
        self.assertTrue(result['isApiError'])
        self.assertEqual(result['status'], 400)
        self.assertEqual(result['message'], 'username already taken')

    def test_today_plan_url_includes_hours_param(self):
        captured = []

        def capture(route):
            captured.append(route.request.url)
            route.fulfill(status=200, content_type="application/json", body="[]")

        self.page.route("**/api/plan/today*", capture)
        self.js("""async () => {
            const { ApiClient } = await import('/static/js/api.js');
            const api = new ApiClient('http://localhost:5000');
            try { await api.getTodayPlan(6); } catch (_) {}
        }""")
        self.assertTrue(any("hours=6" in url for url in captured),
                        f"hours=6 not in captured URLs: {captured}")

    def test_week_plan_url_includes_hours_and_days_params(self):
        captured = []

        def capture(route):
            captured.append(route.request.url)
            route.fulfill(status=200, content_type="application/json", body="[]")

        self.page.route("**/api/plan/week*", capture)
        self.js("""async () => {
            const { ApiClient } = await import('/static/js/api.js');
            const api = new ApiClient('http://localhost:5000');
            try { await api.getWeekPlan(8, 7); } catch (_) {}
        }""")
        self.assertTrue(any("hours=8" in url and "days=7" in url for url in captured),
                        f"expected hours=8&days=7 in {captured}")

    def test_204_response_returns_null(self):
        self.page.route("**/api/auth/logout", lambda route: route.fulfill(status=204))
        result = self.js("""async () => {
            const { ApiClient } = await import('/static/js/api.js');
            const api = new ApiClient('http://localhost:5000');
            try { return await api.logout(); } catch (_) { return 'error'; }
        }""")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# views.js — renderWeekPlan weekday alignment (Phase 14)
# ---------------------------------------------------------------------------

class WeekPlanViewsTest(_PlaywrightBase):

    # Minimal fake day matching the shape Views.renderWeekPlan expects.
    _DAY = {"date": "2099-01-07", "available_hours": 6, "planned_hours_total": 2,
             "entries": [], "deadlines": []}

    def test_render_week_plan_adds_weekday_header_cells(self):
        html = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            Views.renderWeekPlan([]);
            return document.getElementById('week-grid').innerHTML;
        }""")
        for label in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            self.assertIn(label, html, f"header '{label}' missing from week grid")

    def test_render_week_plan_next_week_overflow_cards_get_past_class(self):
        # Days after Sunday of the current calendar week should be muted.
        # +8 days from today is always in next week regardless of today's weekday.
        import datetime
        next_week_date = (datetime.date.today() + datetime.timedelta(days=8)).isoformat()
        has_past = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            const day = {{"date": "{next_week_date}", "available_hours": 6,
                         "planned_hours_total": 0, "entries": [], "deadlines": []}};
            Views.renderWeekPlan([day]);
            return document.getElementById('week-grid').querySelector('.day-card-past') !== null;
        }}""")
        self.assertTrue(has_past)

    def test_render_week_plan_next_week_cards_placed_before_current_week(self):
        # With 7 rolling days, next-week overflow cards (todayOffset of them)
        # must appear BEFORE current-week cards in DOM order so they occupy
        # the Mon-…-(today-1) columns and today lands in its real weekday column.
        import datetime
        today = datetime.date.today()
        today_offset = today.weekday()
        days = [
            {"date": (today + datetime.timedelta(days=i)).isoformat(),
             "available_hours": 6, "planned_hours_total": 0, "entries": [], "deadlines": []}
            for i in range(7)
        ]
        past_count = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            Views.renderWeekPlan({json.dumps(days)});
            return document.getElementById('week-grid').querySelectorAll('.day-card-past').length;
        }}""")
        self.assertEqual(past_count, today_offset)

    def test_render_week_plan_produces_day_card_for_each_entry(self):
        today = date.today().isoformat()
        result = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            const day = {{"date": "{today}", "available_hours": 6,
                         "planned_hours_total": 2, "entries": [], "deadlines": []}};
            Views.renderWeekPlan([day, day, day]);
            const grid = document.getElementById('week-grid');
            // Exclude both next-week-muted and trailing-blank cards — only current-week cards.
            return grid.querySelectorAll('.day-card:not(.day-card-past):not(.day-card-blank)').length;
        }}""")
        self.assertEqual(result, 3)

    def test_render_week_plan_today_card_gets_is_today_class(self):
        today = date.today().isoformat()
        has_class = self.js(f"""async () => {{
            const {{ Views }} = await import('/static/js/views.js');
            const day = {{"date": "{today}", "available_hours": 6,
                         "planned_hours_total": 0, "entries": [], "deadlines": []}};
            Views.renderWeekPlan([day]);
            return document.getElementById('week-grid').querySelector('.is-today') !== null;
        }}""")
        self.assertTrue(has_class)

    def test_render_week_plan_month_mode_adds_trailing_blanks_to_complete_row(self):
        import datetime
        today_offset = datetime.date.today().weekday()
        # Three data days; trailing blank count = (7 - (offset + 3) % 7) % 7.
        # Leading cards are .day-card-past (not .day-card-blank), so only
        # trailing fillers appear as .day-card-blank.
        expected_trailing = (7 - (today_offset + 3) % 7) % 7
        result = self.js("""async () => {
            const { Views } = await import('/static/js/views.js');
            const day = {"date": "2099-01-07", "available_hours": 6,
                         "planned_hours_total": 0, "entries": [], "deadlines": []};
            Views.renderWeekPlan([day, day, day], { monthMode: true });
            const grid = document.getElementById('week-grid');
            return grid.querySelectorAll('.day-card-blank').length;
        }""")
        self.assertEqual(result, expected_trailing)

    def test_month_tab_button_exists_in_html(self):
        exists = self.js("""() => document.getElementById('plan-tab-month') !== null""")
        self.assertTrue(exists)

    def test_month_tab_click_shows_week_view_panel(self):
        result = self.js("""async () => {
            const btn = document.getElementById('plan-tab-month');
            btn.click();
            const weekView = document.getElementById('plan-week-view');
            const todayView = document.getElementById('plan-today-view');
            return {
                weekHidden: weekView.classList.contains('hidden'),
                todayHidden: todayView.classList.contains('hidden'),
                monthActive: btn.classList.contains('active'),
            };
        }""")
        self.assertFalse(result['weekHidden'])
        self.assertTrue(result['todayHidden'])
        self.assertTrue(result['monthActive'])


if __name__ == "__main__":
    unittest.main()
