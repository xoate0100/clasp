#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue Query Knowledge Service
Queries GitHub Issues API for similar issues and proposed fixes.
Part of Phase 2: Real-Time Learning system.
"""

import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)


class IssueKnowledgeBase:
    """Query GitHub Issues for similar issues and fixes."""
    
    def __init__(self, template_repo: str, token: Optional[str] = None):
        """
        Initialize issue knowledge base.
        
        Args:
            template_repo: GitHub repository in format "owner/repo"
            token: GitHub API token (defaults to GITHUB_TOKEN env var)
        """
        self.template_repo = template_repo
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.cache_dir = pathlib.Path("6_ai_runtime_context/issue_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(hours=1)
        self.api_base = "https://api.github.com"
    
    def query_similar_issues(
        self,
        issue_description: str,
        category: str = "feedback",
        labels: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Query for similar issues using GitHub Issues API search.
        
        Args:
            issue_description: Description of the issue to find similar ones for
            category: Issue category (default: "feedback")
            labels: Optional list of labels to filter by
        
        Returns:
            List of matching issues with proposed fixes and similarity scores
        """
        # Check cache first
        cache_key = self._generate_cache_key(issue_description, category)
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # Build search query
        search_query = self._build_search_query(issue_description, category, labels)
        
        # Query GitHub API
        issues = self._search_github_issues(search_query)
        
        # Extract proposed fixes from comments and calculate similarity
        enriched_issues = []
        for issue in issues:
            proposed_fixes = self._extract_proposed_fixes(issue.get("number", 0))
            similarity = self._calculate_similarity(
                issue_description,
                issue.get("body", "") or issue.get("title", "")
            )
            
            enriched_issues.append({
                **issue,
                "proposed_fixes": proposed_fixes,
                "similarity_score": similarity
            })
        
        # Sort by similarity (highest first)
        enriched_issues.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)
        
        # Cache results
        self._save_to_cache(cache_key, enriched_issues)
        
        return enriched_issues
    
    def _build_search_query(
        self,
        description: str,
        category: str,
        labels: Optional[List[str]]
    ) -> str:
        """Build GitHub Issues search query."""
        query_parts = [
            f"repo:{self.template_repo}",
            "is:issue",
        ]
        
        # Add category as label if provided
        if category:
            query_parts.append(f"label:{category}")
        
        # Add additional labels
        if labels:
            for label in labels:
                query_parts.append(f"label:{label}")
        
        # Extract keywords from description
        keywords = self._extract_keywords(description)
        if keywords:
            # Add keywords to search (limit to avoid query length issues)
            query_parts.extend(keywords[:5])
        
        return " ".join(query_parts)
    
    def _search_github_issues(self, search_query: str) -> List[Dict]:
        """
        Search GitHub Issues API.
        
        Args:
            search_query: GitHub search query string
        
        Returns:
            List of issue dictionaries
        """
        if not self.token:
            print("WARN: GITHUB_TOKEN not set. Cannot query GitHub API.")
            return []
        
        url = f"{self.api_base}/search/issues"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
        }
        params = {
            "q": search_query,
            "per_page": 10,  # Limit results
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"WARN: GitHub API error: {response.status_code}")
                if response.status_code == 403:
                    print("  Rate limit exceeded or insufficient permissions")
                return []
            
            data = response.json()
            return data.get("items", [])
        
        except requests.exceptions.RequestException as e:
            print(f"WARN: Failed to query GitHub API: {e}")
            return []
    
    def _get_issue_comments(self, issue_number: int) -> List[Dict]:
        """
        Get comments for a specific issue.
        
        Args:
            issue_number: GitHub issue number
        
        Returns:
            List of comment dictionaries
        """
        if not self.token:
            return []
        
        owner, repo = self._parse_repo(self.template_repo)
        if not owner or not repo:
            return []
        
        url = f"{self.api_base}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.token}",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                return []
            
            return response.json()
        
        except requests.exceptions.RequestException:
            return []
    
    def _extract_proposed_fixes(self, issue_number: int) -> List[Dict]:
        """
        Extract proposed fixes from issue comments.
        
        Args:
            issue_number: GitHub issue number
        
        Returns:
            List of proposed fixes with metadata
        """
        comments = self._get_issue_comments(issue_number)
        fixes = []
        
        # Look for comments that contain fix indicators
        fix_indicators = [
            "fix", "solution", "workaround", "resolved", "fixed",
            "patch", "update", "change", "modify"
        ]
        
        for comment in comments:
            body = comment.get("body", "").lower()
            
            # Check if comment contains fix-related keywords
            if any(indicator in body for indicator in fix_indicators):
                fixes.append({
                    "body": comment.get("body", ""),
                    "author": comment.get("user", {}).get("login", "unknown"),
                    "created_at": comment.get("created_at", ""),
                    "url": comment.get("html_url", "")
                })
        
        return fixes
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for search.
        
        Args:
            text: Text to extract keywords from
        
        Returns:
            List of keywords
        """
        # Remove common words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "is", "are", "was", "were", "be",
            "been", "have", "has", "had", "do", "does", "did", "will",
            "would", "should", "could", "may", "might", "can", "this",
            "that", "these", "those", "i", "you", "he", "she", "it", "we", "they"
        }
        
        # Extract words (alphanumeric, at least 3 characters)
        words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', text.lower())
        
        # Filter out stop words and return unique keywords
        keywords = [w for w in words if w not in stop_words]
        return list(set(keywords))  # Remove duplicates
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using simple word overlap.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Extract keywords from both texts
        keywords1 = set(self._extract_keywords(text1))
        keywords2 = set(self._extract_keywords(text2))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _generate_cache_key(self, description: str, category: str) -> str:
        """
        Generate cache key from description and category.
        
        Args:
            description: Issue description
            category: Issue category
        
        Returns:
            Cache key string
        """
        # Create a hash-like key from description and category
        import hashlib
        key_string = f"{category}:{description[:100]}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """
        Load cached results if available and not expired.
        
        Args:
            cache_key: Cache key
        
        Returns:
            Cached data or None if not available/expired
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # Check if cache is expired
            timestamp_str = cache_data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str)
                if datetime.now() - timestamp > self.cache_ttl:
                    return None
            
            return cache_data.get("data")
        
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
    
    def _save_to_cache(self, cache_key: str, data: List[Dict]) -> None:
        """
        Save results to cache.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
        except (IOError, OSError) as e:
            print(f"WARN: Failed to save cache: {e}")
    
    def _parse_repo(self, repo_string: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse repository string into owner and repo.
        
        Args:
            repo_string: Repository in format "owner/repo"
        
        Returns:
            Tuple of (owner, repo) or (None, None) if invalid
        """
        parts = repo_string.split("/")
        if len(parts) == 2:
            return parts[0], parts[1]
        return None, None


def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query GitHub Issues for similar issues and fixes"
    )
    parser.add_argument(
        "description",
        help="Issue description to search for"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository (format: owner/repo)"
    )
    parser.add_argument(
        "--category",
        default="feedback",
        help="Issue category (default: feedback)"
    )
    parser.add_argument(
        "--labels",
        nargs="*",
        help="Additional labels to filter by"
    )
    parser.add_argument(
        "--token",
        help="GitHub API token (defaults to GITHUB_TOKEN env var)"
    )
    
    args = parser.parse_args()
    
    kb = IssueKnowledgeBase(args.repo, args.token)
    results = kb.query_similar_issues(
        args.description,
        args.category,
        args.labels
    )
    
    print(f"Found {len(results)} similar issues:")
    for i, issue in enumerate(results[:5], 1):  # Show top 5
        print(f"\n{i}. Issue #{issue.get('number')}: {issue.get('title')}")
        print(f"   Similarity: {issue.get('similarity_score', 0):.2%}")
        print(f"   URL: {issue.get('html_url', 'N/A')}")
        if issue.get('proposed_fixes'):
            print(f"   Proposed fixes: {len(issue['proposed_fixes'])}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
