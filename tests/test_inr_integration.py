from decimal import Decimal
from uuid import uuid4


def test_inr_financial_journey(client):
    ids, headers = [], []
    for name in ('Alice', 'Bob'):
        credentials = {'email': f'{uuid4().hex}@example.com', 'password': 'TestPassword123!'}
        r = client.post('/auth/register', json={**credentials, 'full_name': name})
        assert r.status_code == 201, r.text
        ids.append(r.json()['id'])
        r = client.post('/auth/login', json=credentials)
        assert r.status_code == 200, r.text
        headers.append({'Authorization': f"Bearer {r.json()['access_token']}"})
    a, b = ids
    ah, bh = headers

    def group(currency):
        r = client.post('/groups', headers=ah, json={'name': f'{currency} test', 'currency': currency})
        assert r.status_code == 201, r.text
        assert r.json()['currency'] == currency
        base = f"/groups/{r.json()['id']}"
        r = client.post(base + '/members', headers=ah, json={'user_id': b})
        assert r.status_code == 201, r.text
        r = client.post(base + '/expenses', headers=ah, json={
            'description': 'Dinner', 'amount': '100.50',
            'splits': [{'user_id': a, 'amount_owed': '50.25'}, {'user_id': b, 'amount_owed': '50.25'}],
        })
        assert r.status_code == 201, r.text
        assert Decimal(r.json()['amount']) == Decimal('100.50')
        return base

    def balances(base, amount):
        for h in (ah, bh):
            r = client.get(base + '/balances', headers=h)
            assert r.status_code == 200, r.text
            assert {x['user_id']: Decimal(x['net_balance']) for x in r.json()['balances']} == {a: Decimal(amount), b: -Decimal(amount)}

    inr, usd = group('INR'), group('USD')
    balances(inr, '50.25')
    balances(usd, '50.25')
    r = client.post(inr + '/payment-requests', headers=ah, json={'debtor_id': b, 'amount': '50.25'})
    assert r.status_code == 201, r.text
    rid = r.json()['id']
    for amount, remaining, fulfilled, status in [('20.10', '30.15', '20.10', 'pending'), ('30.15', '0.00', '50.25', 'fulfilled')]:
        r = client.post(inr + '/payments', headers=bh, json={'to_user_id': a, 'amount': amount})
        assert r.status_code == 201, r.text
        assert r.json()['status'] == 'pending'
        balances(inr, '50.25' if status == 'pending' else '30.15')
        r = client.post(f"{inr}/payments/{r.json()['id']}/confirm", headers=ah)
        assert r.status_code == 200, r.text
        balances(inr, remaining)
        balances(usd, '50.25')
        r = client.get(inr + '/payment-requests', headers=bh)
        assert r.status_code == 200, r.text
        item = next(x for x in r.json() if x['id'] == rid)
        assert Decimal(item['fulfilled_amount']) == Decimal(fulfilled)
        assert item['status'] == status
