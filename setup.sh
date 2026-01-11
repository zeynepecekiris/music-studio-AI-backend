#!/bin/bash

echo "🎵 Setting up Musician API Backend..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python packages..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads/music
mkdir -p uploads/voices
mkdir -p logs

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your API keys"
fi

# Make run script executable
chmod +x run.py

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   - OPENAI_API_KEY=your_openai_key"
echo "   - ELEVENLABS_API_KEY=your_elevenlabs_key"
echo ""
echo "2. Run the server:"
echo "   python run.py"
echo ""
echo "3. Visit http://localhost:8000/docs for API documentation"
