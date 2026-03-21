# Requirements

## Glossary

* **Playlist:** List of Spotify tracks curated under a coherent topic, e.g. listening mood, cultural era.
* **User Library:** The complete collection of tracks present across all of a user's Spotify playlists.
* **Track Metadata:** Information about a track including artist, album, duration, and audio features (e.g., tempo, energy, danceability).

## 1 Functional Requirements

### 1.1 User Requirements

* 1.1.1 A user shall be able to enter natural language text describing their desired playlist.
* 1.1.2 A user shall be able to authenticate with their Spotify account.
* 1.1.3 A user shall receive a playlist containing only tracks from their existing Spotify playlists.

### 1.2 System Requirements

#### 1.2.1 Spotify Integration

* 1.2.1.1 The system shall authenticate users via Spotify OAuth.
* 1.2.1.2 The system shall retrieve all playlists associated with the authenticated user's Spotify account.
* 1.2.1.3 The system shall extract all tracks from the user's playlists.
* 1.2.1.4 The system shall retrieve track metadata including:
  - Track name
  - Artist(s)
  - Album
  - Duration
  - Audio features (energy, danceability, valence, tempo, etc.)
* 1.2.1.5 The system shall maintain a searchable library of the user's tracks.

#### 1.2.2 Natural Language Processing

* 1.2.2.1 The system shall receive natural language text input from the user describing their desired playlist.
* 1.2.2.2 The system shall extract playlist characteristics from user input, including:
  - Desired duration (e.g., "one hour", "30 minutes")
  - Mood descriptors (e.g., "jazzy", "joyful", "energetic")
  - Genre preferences
  - Other contextual requirements

#### 1.2.3 LLM Integration

* 1.2.3.1 The system shall construct a prompt containing:
  - User's natural language request
  - The user's track library with relevant metadata
  - Instructions to select tracks only from the provided library
* 1.2.3.2 The system shall send the constructed prompt to an LLM instance.
* 1.2.3.3 The system shall receive track recommendations from the LLM instance.
* 1.2.3.4 The system shall validate that all recommended tracks exist in the user's library.

#### 1.2.4 Playlist Generation

* 1.2.4.1 The system shall generate a playlist consisting only of tracks from the user's existing playlists.
* 1.2.4.2 The system shall ensure the total duration of recommended tracks matches the user's requested duration (within a reasonable tolerance).
* 1.2.4.3 The system shall display the recommended playlist to the user, including:
  - Track names
  - Artists
  - Total playlist duration
* 1.2.4.4 The system should provide the option to create/save the recommended playlist to the user's Spotify account.

## 2 Non-functional Requirements

### 2.1 Performance

* 2.1.1 The system should retrieve user's playlist data within 10 seconds for libraries up to 10,000 tracks.
* 2.1.2 The system should generate playlist recommendations within 30 seconds of user input submission.

### 2.2 Usability

* 2.2.1 The system shall provide clear feedback during playlist generation (e.g., "Fetching your playlists...", "Analyzing tracks...").
* 2.2.2 The system shall handle common user input variations (e.g., "1 hour" vs "60 minutes" vs "one hour").

### 2.3 Security

* 2.3.1 The system shall securely store Spotify authentication tokens.
* 2.3.2 The system shall not expose user's playlist data to unauthorized parties.

### 2.4 Scalability

* 2.4.1 The system should support users with up to 50 playlists.
* 2.4.2 The system should handle track libraries of up to 10,000 songs.

## 3 Constraints

* 3.1 The system must comply with Spotify API terms of service and rate limits.
* 3.2 The system requires an active internet connection to function.
* 3.3 Recommendations are limited to tracks that exist in the user's current Spotify playlists.