# BGG Flashcards

A mobile application for creating and studying flashcards for board games from BoardGameGeek.

## Project Structure

- `api/`: FastAPI backend for iOS compatibility
- `client/`: Client code for API communication
- `models/`: Data models
- `pages/`: UI pages for the application
- `assets/`: Application assets like icons

## Setup & Installation

### Development Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   pip install -r api/requirements.txt
   ```

2. Run the API server:
   ```
   python run_api.py
   ```

3. Run the application:
   ```
   python app.py
   ```

### Building for iOS

#### Prerequisites:

- macOS with Xcode 15+ installed
- Apple Developer account
- CocoaPods 1.16+

#### Build Steps:

1. Update your Developer Team ID in `flet.yaml`

2. Install flet CLI tools:
   ```
   pip install flet-cli
   ```

3. Build the iOS app:
   ```
   flet build ipa --build-version 1.0.0 --build-number 1
   ```

4. The IPA file will be created in the `build/ios/ipa` directory

5. Install through TestFlight or directly to device using Apple Configurator

## iOS Deployment Architecture

The iOS application uses a client-server architecture:

1. **Backend**: FastAPI server that handles database operations
   - Runs on a server accessible to your iOS device
   - Manages PostgreSQL database connections
   - Provides RESTful API endpoints

2. **iOS App**: Flet-based UI application
   - Communicates with backend via REST API
   - Stores user authentication tokens securely
   - Provides offline caching for flashcards

## API Server Configuration

For iOS deployment, you need to:

1. Host the API server on a public-facing server
2. Update the `base_url` in `client/api_client.py` to point to your server
3. Configure proper SSL/TLS for secure communication
4. Set up proper authentication and rate limiting

## License

This project is private and not available for redistribution.