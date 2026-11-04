"""Use Frappe's authenticated API so Desk boot and later requests agree on language."""
import json


def change_script(origin, language):
    if language not in ('ar', 'en'):
        raise ValueError('Unsupported language')
    # Executed only in the selected WebKit page, with its own session and CSRF
    # token. No credentials leave the page and no native command bridge exists.
    return '''
const origin = ORIGIN;
const language = LANGUAGE;
if (window.location.origin !== origin) throw new Error('Unexpected page origin');
const session = await fetch('/api/method/frappe.auth.get_logged_user', {credentials: 'same-origin'});
if (session.status === 401 || session.status === 403) {
    document.cookie = 'preferred_language=' + language + '; Path=/; SameSite=Lax' +
        (window.location.protocol === 'https:' ? '; Secure' : '');
    return language;
}
if (!session.ok) throw new Error('Could not read the current session');
const user = (await session.json()).message;
const token = window.frappe?.csrf_token || window.csrf_token;
if (!user || user === 'Guest' || !token) throw new Error('Sign in before changing your account language');
const response = await fetch('/api/method/frappe.client.set_value', {
    method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': token},
    body: JSON.stringify({doctype: 'User', name: user, fieldname: 'language', value: language})
});
if (!response.ok) throw new Error('The server refused to save the account language');
const result = await response.json();
if (result.message?.language !== language) throw new Error('Language change was not confirmed');
return language;
'''.replace('ORIGIN', json.dumps(origin)).replace('LANGUAGE', json.dumps(language))
