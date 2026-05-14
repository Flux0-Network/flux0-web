# Discord Verification Bot

A Discord bot that lets users create accounts and verify themselves via a code sent to their DMs.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your bot token:
   ```bash
   cp .env.example .env
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```

## Commands

- `/setup` — Posts the account creation panel in the current channel
- `/account` — Shows your account ID and verification status

## Flow

1. User clicks **Create Account** → account is created and a code is sent via DM
2. User clicks **Code eingeben** → enters the code in a modal
3. On success, the verified role is assigned automatically
