import asyncio
import sys
sys.path.append('src')

from src.app.core.config import settings
from src.app.services.openai_service import OpenAIService

async def test_openai():
    service = OpenAIService()
    
    print("🧪 Testing OpenAI Connection...")
    print(f"Using model: {settings.OPENAI_MODEL}")
    
    try:
        # 簡單的測試提示
        result = await service.generate_completion(
            prompt="Say 'Hello, Amazon Insights Platform is ready!' in 10 words or less.",
            max_tokens=50
        )
        print(f"✅ OpenAI Response: {result}")
        return True
    except Exception as e:
        print(f"❌ OpenAI Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai())
    sys.exit(0 if success else 1)
