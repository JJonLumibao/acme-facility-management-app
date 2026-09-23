# Coding Workshop - Frontend Code

## Overview

This folder contains a React + TypeScript frontend for the ACME facility incident management app.

## Prerequisites

- React - JavaScript library for building user interfaces
- TypeScript - typed superset of JavaScript
- React Router - Client-side routing for React
- Material UI - Comprehensive UI component library

## Structure

```
coding-workshop-participant/
├── frontend/              # React frontend
│   ├── public/              # Public assets
│   ├── src/                 # Source code
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components (layout/common/incidents/facilities/engineers)
│   │   ├── services/          # API client + per-resource service modules
│   │   ├── context/           # AuthContext (current user + login/register/logout)
│   │   ├── types/             # Shared TypeScript types matching backend entities
│   │   ├── styles/             # theme.ts (MUI theme) + all CSS files
│   │   └── App.tsx            # Main app (routes)
│   ├── .env.sample          # React environment variables
│   ├── eslint.config.js     # ESLint TS tool configuration
│   ├── index.html           # Landing page
│   ├── package.json         # App metadata with dependencies
│   ├── README.md            # Frontend guide (YOU ARE HERE)
│   ├── tsconfig*.json       # TypeScript configuration
│   └── vite.config.ts       # Vite build tool configuration
├── ...
```

## Usage

### Local Development

To run your application locally:

```sh
./bin/start-dev.sh
```

To view your application, open the browser and navigate to `http://localhost:3000`.

### Cloud Deployment

To deploy your frontend to AWS:

```sh
./bin/deploy-frontend.sh
```

To view your application, open the browser and navigate to CloudFront URL.

## Clean Up

To remove all deployed resources (including frontend):

```sh
./bin/cleanup-environment.sh
```

**Warning**: This removes all infra resources. Cannot be undone.
