import httpx
import asyncio

async def run():
    async with httpx.AsyncClient(timeout=30) as client:
        print("Creating session...")
        r = await client.post('http://localhost:8000/api/sessions/', json={})
        s = r.json()['session_id']
        print('Session:', s)
        
        print("Uploading mock message...")
        # Since we just want to get to the interrupt state
        # the graph just needs to run extract_card -> request_confirmation
        # In extract_card we read state.get("file_data"). If we just pass a fake image it's fine.
        with open('app/main.py', 'rb') as f:
            files = {'image': ('dummy.png', f, 'image/png')}
            r2 = await client.post(f'http://localhost:8000/api/sessions/{s}/messages', data={'text': 'Here is my card'}, files=files)
        print('Extract:', r2.json())
        
        print("Confirming...")
        r3 = await client.post(f'http://localhost:8000/api/sessions/{s}/confirm', json={'name': 'Bob Jones', 'phone': '555-1234', 'email': 'bob@hvl.com', 'company': 'HVL Corp'})
        print('Confirm:', r3.json())

if __name__ == "__main__":
    asyncio.run(run())
