# Tracker.gg Stats API

This API allows you to fetch statistics for Valorant players, including current and all-time statistics. The API is built using FastAPI and utilizes web scraping to gather player data from [Tracker.gg](https://tracker.gg/).

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
  - [Valorant](#Valorant)
    - [Get Current Act Stats](#get-current-act-stats)
    - [Get All Seasons Stats](#get-all-seasons-stats)
- [Response Model](#response-model)
- [Error Handling](#error-handling)
- [License](#license)

## Features

- Fetch current act statistics for a given Valorant player.
- Fetch all-time statistics across seasons for a given Valorant player.
- API key authentication for secure access.

## Getting Started

### Prerequisites

- Python 3.7 or higher

### Installation

1. Clone the repository:

```bash
git@github.com:aydenjahola/tracker-gg-api.git
cd tracker-gg-api.git
```

2. Create virtual environment

```bash
python3 -m venv vevn
```

3. Actiave the virtual environemnt

```bash
source venv/bin/activate # For Linux
source venv/Scripts/Actiave # For Windows
```

4. Install the required packages:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root of the project directory and add your API keys:

```env
API_KEYS=your_api_key # Create a new key using the openssl command
FLARESOLVERR_URL=your_flare_solver_url
TRN_API_KEY=your_trn_api_key
```

Make sure to replace `your_api_key`, `your_flare_solver_url`, and `your_trn_api_key` with your actual values.

## API Endpoints

### Valorant

#### Get Current Act Stats

**Endpoint:** `GET /valorant/player/{username}/current`

**Description:** Fetch the current act statistics for a given Valorant player.

**Parameters:**

- `username`: The Riot username of the player (eg. Shitter#1234).
- `X-API-Key`: Your API key (header).

#### Get All Seasons Stats

**Endpoint:** `GET /valorant/player/{username}/all`

**Description:** Fetch all seasons' statistics for a given Valorant player.

**Parameters:**

- `username`: The Riot username of the player (eg. Shitter#1234).
- `X-API-Key`: Your API key (header).

## Error Handling

- **403 Forbidden:** If the API key is invalid.
- **404 Not Found:** If the player's stats cannot be found.

## License

This project is licensed under the [GPL-3.0 license ](./LICENSE). See the LICENSE file for details.

---

Feel free to reach out for any questions or contributions to the project!
