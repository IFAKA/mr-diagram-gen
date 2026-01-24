#!/bin/bash
# Create a test repository for local testing of mr-diagram-gen

set -e

TEST_DIR="${1:-./test-project}"

echo "Creating test repository at $TEST_DIR..."

# Create directory
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Initialize git repo
git init

# Configure git user (for commits)
git config user.name "Test User"
git config user.email "test@example.com"

# Create a React project structure
echo "Creating React project structure..."

mkdir -p src/components src/hooks src/pages src/api

# Create package.json
cat > package.json << 'EOF'
{
  "name": "test-react-app",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }
}
EOF

# Create initial components
cat > src/components/App.tsx << 'EOF'
import React from 'react';
import { Header } from './Header';

export function App() {
  return (
    <div>
      <Header />
      <main>Welcome to the app</main>
    </div>
  );
}
EOF

cat > src/components/Header.tsx << 'EOF'
import React from 'react';

export function Header() {
  return (
    <header>
      <h1>My App</h1>
    </header>
  );
}
EOF

# Create README
cat > README.md << 'EOF'
# Test React App

A test repository for mr-diagram-gen.
EOF

# Initial commit
git add .
git commit -m "Initial commit: React project setup"

# Create a feature branch with changes
git checkout -b feature/dashboard

# Add new components
cat > src/components/Dashboard.tsx << 'EOF'
import React from 'react';
import { UserCard } from './UserCard';
import { StatsPanel } from './StatsPanel';

interface DashboardProps {
  userId: string;
}

export function Dashboard({ userId }: DashboardProps) {
  return (
    <div className="dashboard">
      <UserCard userId={userId} />
      <StatsPanel userId={userId} />
    </div>
  );
}
EOF

cat > src/components/UserCard.tsx << 'EOF'
import React from 'react';
import { useUser } from '../hooks/useUser';

interface UserCardProps {
  userId: string;
}

export function UserCard({ userId }: UserCardProps) {
  const { user, loading } = useUser(userId);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="user-card">
      <img src={user?.avatar} alt={user?.name} />
      <h2>{user?.name}</h2>
      <p>{user?.email}</p>
    </div>
  );
}
EOF

cat > src/components/StatsPanel.tsx << 'EOF'
import React from 'react';

interface StatsPanelProps {
  userId: string;
}

export function StatsPanel({ userId }: StatsPanelProps) {
  return (
    <div className="stats-panel">
      <div className="stat">
        <span className="label">Posts</span>
        <span className="value">42</span>
      </div>
      <div className="stat">
        <span className="label">Followers</span>
        <span className="value">1.2k</span>
      </div>
    </div>
  );
}
EOF

# Add a custom hook
cat > src/hooks/useUser.ts << 'EOF'
import { useState, useEffect } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
  avatar: string;
}

export function useUser(userId: string) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        setUser(data);
      } finally {
        setLoading(false);
      }
    }

    fetchUser();
  }, [userId]);

  return { user, loading };
}
EOF

# Add an API route
cat > src/api/users.ts << 'EOF'
import { Request, Response } from 'express';

export async function getUser(req: Request, res: Response) {
  const { id } = req.params;

  // Fetch user from database
  const user = await db.users.findById(id);

  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }

  return res.json(user);
}

export async function updateUser(req: Request, res: Response) {
  const { id } = req.params;
  const updates = req.body;

  const user = await db.users.update(id, updates);
  return res.json(user);
}
EOF

# Update App to include Dashboard
cat > src/components/App.tsx << 'EOF'
import React from 'react';
import { Header } from './Header';
import { Dashboard } from './Dashboard';

export function App() {
  return (
    <div>
      <Header />
      <Dashboard userId="123" />
    </div>
  );
}
EOF

# Commit the changes
git add .
git commit -m "Add dashboard feature with user card and stats panel

- New Dashboard component with user info and stats
- UserCard component with avatar and details
- StatsPanel component for user metrics
- useUser hook for data fetching
- API routes for user operations"

echo ""
echo "Test repository created successfully!"
echo ""
echo "Structure:"
echo "  $TEST_DIR/"
echo "  ├── package.json"
echo "  ├── README.md"
echo "  └── src/"
echo "      ├── api/"
echo "      │   └── users.ts (NEW)"
echo "      ├── components/"
echo "      │   ├── App.tsx (MODIFIED)"
echo "      │   ├── Dashboard.tsx (NEW)"
echo "      │   ├── Header.tsx"
echo "      │   ├── StatsPanel.tsx (NEW)"
echo "      │   └── UserCard.tsx (NEW)"
echo "      └── hooks/"
echo "          └── useUser.ts (NEW)"
echo ""
echo "To test mr-diagram-gen:"
echo "  cd $TEST_DIR"
echo "  mr-diagram-gen analyze --local --mock-llm"
echo ""
