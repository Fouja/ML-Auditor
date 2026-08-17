"""
Tool executor — runs function calls from the agent.
Bridges NIM tool calls to actual backend services.
"""

import logging
from typing import Any, Dict

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes tool calls from the agent.
    Each tool maps to a backend service or API call.
    """

    def __init__(self, user):
        self.user = user

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Route and execute a tool call."""
        handler = getattr(self, f"_exec_{tool_name}", None)
        if handler:
            try:
                return await handler(args)
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    # ─── Note tools ──────────────────────────────────────────────────

    async def _exec_create_note(self, args: Dict) -> Dict:
        from apps.workspace.models import Note

        def _create():
            return Note.objects.create(
                user=self.user,
                title=args["title"],
                content=args.get("content", ""),
                format=args.get("format", "note"),
                tags=args.get("tags", []),
            )

        note = await sync_to_async(_create)()
        return {"success": True, "note_id": str(note.id), "title": note.title, "format": note.format}

    async def _exec_get_notes(self, args: Dict) -> Dict:
        from apps.workspace.models import Note

        def _list():
            qs = Note.objects.filter(user=self.user)
            if args.get("format"):
                qs = qs.filter(format=args["format"])
            if args.get("tag"):
                qs = qs.filter(tags__contains=args["tag"])
            if args.get("query"):
                qs = qs.filter(title__icontains=args["query"]) | qs.filter(content__icontains=args["query"])
            return list(qs[:20])

        notes = await sync_to_async(_list)()
        return {
            "success": True,
            "notes": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "content_preview": n.content[:200],
                    "format": n.format,
                    "tags": n.tags,
                    "updated_at": n.updated_at.isoformat(),
                }
                for n in notes
            ],
            "count": len(notes),
        }

    async def _exec_update_note(self, args: Dict) -> Dict:
        from apps.workspace.models import Note

        def _update():
            try:
                note = Note.objects.get(id=args["note_id"], user=self.user)
                for field in ["title", "content", "format", "tags"]:
                    if field in args:
                        setattr(note, field, args[field])
                note.save()
                return note
            except Note.DoesNotExist:
                return None

        note = await sync_to_async(_update)()
        if note:
            return {"success": True, "note_id": str(note.id), "title": note.title}
        return {"success": False, "error": "Note not found"}

    async def _exec_organize_notes(self, args: Dict) -> Dict:
        from apps.workspace.models import Note

        def _fetch_notes():
            return list(Note.objects.filter(id__in=args["note_ids"], user=self.user))

        notes = await sync_to_async(_fetch_notes)()
        if not notes:
            return {"success": False, "error": "No notes found"}

        combined = "\n\n".join(
            f"--- {n.title} ---\n{n.content}" for n in notes
        )
        target = args.get("target_format", "article")
        style = args.get("style", "professional")
        output_title = args.get("title", f"Organized {target}")

        return {
            "success": True,
            "organized_content": combined,
            "target_format": target,
            "style": style,
            "suggested_title": output_title,
            "message": f"Ready to generate {target} from {len(notes)} notes. "
                      f"The AI can now format this into a {style} {target}.",
        }

    # ─── Task tools ──────────────────────────────────────────────────

    async def _exec_list_tasks(self, args: Dict) -> Dict:
        from apps.workspace.models import Task

        def _list():
            qs = Task.objects.filter(user=self.user).order_by("position", "-created_at")
            if args.get("status"):
                qs = qs.filter(status=args["status"])
            if args.get("query"):
                q = args["query"]
                qs = qs.filter(title__icontains=q) | qs.filter(description__icontains=q)
            return list(qs[:50])

        tasks = await sync_to_async(_list)()
        return {
            "success": True,
            "tasks": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "tags": t.tags,
                    "position": t.position,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat(),
                }
                for t in tasks
            ],
            "count": len(tasks),
        }

    async def _exec_create_task(self, args: Dict) -> Dict:
        from apps.workspace.models import Task

        def _create():
            return Task.objects.create(
                user=self.user,
                title=args["title"],
                description=args.get("description", ""),
                status=args.get("status", "todo"),
                priority=args.get("priority", "medium"),
            )

        task = await sync_to_async(_create)()
        return {"success": True, "task_id": str(task.id), "title": task.title}

    # ─── Email tools ─────────────────────────────────────────────────

    async def _exec_send_email(self, args: Dict) -> Dict:
        recipient = (args.get("to") or "").strip()
        if "@" not in recipient or "." not in recipient.split("@")[-1]:
            return {
                "success": False,
                "error": "No valid recipient email address provided. Please ask the user for the exact email address before sending.",
            }
        user = self.user
        if user.email_imap_host and user.email_imap_password:
            from apps.users.services.email_client import EmailClient

            client = EmailClient(
                email_address=user.email,
                password=user.email_imap_password,
                provider=user.email_provider or "custom",
                smtp_host=user.email_smtp_host,
                smtp_port=user.email_smtp_port,
                use_ssl=user.email_use_ssl,
            )
            client.send_message(
                to=args["to"],
                subject=args["subject"],
                body=args["body"],
                cc=args.get("cc"),
            )
            return {"success": True, "to": args["to"], "subject": args["subject"]}
        elif user.google_access_token:
            from apps.users.services import GmailClient

            gmail = GmailClient(user)
            gmail.send_message(
                to=args["to"],
                subject=args["subject"],
                body=args["body"],
                cc=args.get("cc"),
            )
            return {"success": True, "to": args["to"], "subject": args["subject"]}
        return {"success": False, "error": "No email provider configured"}

    async def _exec_search_email(self, args: Dict) -> Dict:
        user = self.user
        if user.email_imap_host and user.email_imap_password:
            from apps.users.services.email_client import EmailClient

            client = EmailClient(
                email_address=user.email,
                password=user.email_imap_password,
                provider=user.email_provider or "custom",
                imap_host=user.email_imap_host,
                imap_port=user.email_imap_port,
                use_ssl=user.email_use_ssl,
            )
            messages = client.search_messages(
                query=args["query"],
                folder=args.get("folder", "INBOX"),
                limit=10,
            )
            return {"success": True, "messages": messages[:5], "count": len(messages)}
        if user.google_access_token:
            # RAG-backed answer: emails are indexed on sync, so answer from the
            # vector store without needing a live Gmail round-trip.
            from apps.document_chunks.services.rag.service import query_rag

            def _rag():
                hits = query_rag(
                    user,
                    args["query"],
                    limit=10,
                    min_score=0.25,
                    sources=["gmail", "email"],
                ).get("results") or []
                return [
                    {
                        "id": h.get("metadata", {}).get("message_id", ""),
                        "subject": h.get("metadata", {}).get("subject", ""),
                        "from": h.get("metadata", {}).get("sender", ""),
                        "date": h.get("metadata", {}).get("date", ""),
                        "snippet": (h.get("content") or "")[:200],
                        "category": h.get("category", ""),
                    }
                    for h in hits
                ]

            messages = await sync_to_async(_rag)()
            return {"success": True, "messages": messages, "count": len(messages)}
        return {"success": False, "error": "No email provider configured"}

    async def _exec_draft_email_reply(self, args: Dict) -> Dict:
        # Draft is generated by the agent, this just stores/returns it
        return {
            "success": True,
            "draft": {
                "to": args.get("original_from", ""),
                "subject": f"Re: {args.get('original_subject', '')}",
                "body": args.get("draft_body", ""),
                "tone": args.get("tone", "professional"),
            },
        }

    # ─── Calendar tools ──────────────────────────────────────────────

    async def _exec_create_calendar_event(self, args: Dict) -> Dict:
        user = self.user
        if user.google_access_token:
            from datetime import datetime

            from apps.users.services import CalendarClient

            cal = CalendarClient(user)
            event = cal.create_event(
                summary=args["summary"],
                start_time=datetime.fromisoformat(args["start_time"]),
                end_time=datetime.fromisoformat(args["end_time"]),
                description=args.get("description"),
                location=args.get("location"),
            )
            return {"success": True, "event_id": event.get("id")}
        return {"success": False, "error": "Google Calendar not connected"}

    # ─── Kijiji tools ────────────────────────────────────────────────

    async def _exec_search_kijiji(self, args: Dict) -> Dict:
        from apps.users.services import KijijiScraperService

        scraper = KijijiScraperService(user=self.user)
        # The scraper does blocking network I/O; run it in a worker thread so a
        # slow/hanging Kijiji request can't stall the agent's event loop.
        listings = await sync_to_async(scraper.search_listings, thread_sensitive=False)(
            query=args["query"],
            location=args.get("location"),
            min_price=args.get("min_price"),
            max_price=args.get("max_price"),
        )
        return {"success": True, "listings": listings[:5], "count": len(listings)}

    # ─── Financial tools ─────────────────────────────────────────────

    async def _exec_analyze_transactions(self, args: Dict) -> Dict:
        user = self.user
        if user.plaid_access_token:
            from datetime import datetime, timedelta

            from apps.users.services import PlaidClient

            plaid = PlaidClient(user)
            days = args.get("days", 30)
            end = datetime.now()
            start = end - timedelta(days=days)
            transactions = plaid.get_transactions(start_date=start, end_date=end)
            # Basic analysis
            total_spent = sum(t.get("amount", 0) for t in transactions)
            categories = {}
            for tx in transactions:
                cat = (
                    tx.get("category", ["Other"])[0] if tx.get("category") else "Other"
                )
                categories[cat] = categories.get(cat, 0) + tx.get("amount", 0)
            return {
                "success": True,
                "total_transactions": len(transactions),
                "total_spent": round(total_spent, 2),
                "by_category": categories,
            }

        # No live Plaid connection: fall back to mock transactions when mock
        # data is enabled, so the chatbot can still answer bank questions.
        mock_transactions = await sync_to_async(self._mock_transactions)()
        if mock_transactions:
            total_spent = sum(t["amount"] for t in mock_transactions)
            by_category = {}
            for tx in mock_transactions:
                by_category[tx["category"]] = by_category.get(tx["category"], 0) + tx["amount"]
            return {
                "success": True,
                "total_transactions": len(mock_transactions),
                "total_spent": round(total_spent, 2),
                "by_category": by_category,
                "transactions": mock_transactions,
                "mock": True,
            }
        return {"success": False, "error": "Plaid not connected"}

    def _mock_transactions(self) -> list:
        """Parse mock bank transactions from the user's plaid mock chunks."""
        try:
            from apps.document_chunks.models import DocumentChunk

            chunks = DocumentChunk.objects.filter(
                stream__user=self.user,
                stream__source_type="plaid",
                stream__payload__mock=True,
            )
            transactions = []
            import re

            for chunk in chunks:
                match = re.match(
                    r"Transaction:\s*(.+?)\s*-\s*\$([\d,]+(?:\.\d+)?)",
                    chunk.content or "",
                )
                if not match:
                    continue
                transactions.append(
                    {
                        "merchant": match.group(1).strip(),
                        "amount": float(match.group(2).replace(",", "")),
                        "category": (chunk.cluster_category or "general").title(),
                    }
                )
            return transactions
        except Exception as e:
            logger.warning(f"Mock transaction fallback failed: {e}")
            return []

    async def _exec_get_bank_statement_pdf(self, args: Dict) -> Dict:
        from .bank_statement_pdf import generate_bank_statement_pdf

        def _generate():
            return generate_bank_statement_pdf(
                self.user,
                month=args.get("month"),
                year=args.get("year"),
                account_id=args.get("account_id"),
            )

        try:
            return await sync_to_async(_generate)()
        except Exception as e:
            logger.error(f"Bank statement generation failed: {e}")
            return {"success": False, "error": str(e)}

    # ─── Jira tools ──────────────────────────────────────────────────

    async def _exec_jira_get_projects(self, args: Dict) -> Dict:
        user = self.user
        if not user.jira_site_url or not user.jira_api_token:
            return {"success": False, "error": "Jira not configured"}

        from apps.users.services.jira_client import JiraClient

        def _get():
            client = JiraClient(
                site_url=user.jira_site_url,
                email=user.jira_email,
                api_token=user.jira_api_token,
            )
            return client.get_projects()

        projects = await sync_to_async(_get)()
        return {"success": True, "projects": projects, "count": len(projects)}

    async def _exec_jira_get_issues(self, args: Dict) -> Dict:
        user = self.user
        if not user.jira_site_url or not user.jira_api_token:
            return {"success": False, "error": "Jira not configured"}

        from apps.users.services.jira_client import JiraClient

        def _get():
            client = JiraClient(
                site_url=user.jira_site_url,
                email=user.jira_email,
                api_token=user.jira_api_token,
            )
            return client.get_issues(
                project_key=args.get("project_key"),
                jql=args.get("jql"),
                max_results=args.get("max_results", 20),
            )

        issues = await sync_to_async(_get)()
        return {"success": True, "issues": issues, "count": len(issues)}

    async def _exec_jira_search(self, args: Dict) -> Dict:
        user = self.user
        if not user.jira_site_url or not user.jira_api_token:
            return {"success": False, "error": "Jira not configured"}

        from apps.users.services.jira_client import JiraClient

        def _search():
            client = JiraClient(
                site_url=user.jira_site_url,
                email=user.jira_email,
                api_token=user.jira_api_token,
            )
            return client.search_for_rag(query=args["query"], max_results=args.get("max_results", 20))

        results = await sync_to_async(_search)()
        return {"success": True, "results": results, "count": len(results)}

    # ─── Canva tools ─────────────────────────────────────────────────

    async def _exec_canva_competitor_monitor(self, args: Dict) -> Dict:
        user = self.user
        if user.canva_access_token:
            from apps.users.services.canva_client import CanvaClient

            client = CanvaClient(user.canva_access_token)
            result = client.track_competitor_keywords(keywords=args.get("keywords", []))
            return {"success": True, **result}
        return {"success": False, "error": "Canva not connected"}

    # ─── Web / news tools (Agent-Reach microservice) ────────────────

    async def _exec_web_search(self, args: Dict) -> Dict:
        from .web_tools_client import web_search

        results = await web_search(
            args["query"], num_results=int(args.get("num_results") or 5)
        )
        return {"success": True, "query": args["query"], "results": results}

    async def _exec_fetch_webpage(self, args: Dict) -> Dict:
        from .web_tools_client import fetch_webpage

        markdown = await fetch_webpage(args["url"])
        return {"success": True, "url": args["url"], "content": markdown[:8000]}

    async def _exec_get_recent_news(self, args: Dict) -> Dict:
        from apps.workspace.models import NewsArticle
        from django.utils import timezone

        def _query():
            days = max(1, int(args.get("days") or 1))
            qs = (
                NewsArticle.objects.filter(
                    feed__user=self.user,
                    created_at__gte=timezone.now() - timezone.timedelta(days=days),
                )
                .select_related("feed")
                .order_by("-created_at")[:15]
            )
            if args.get("query"):
                qs = [
                    a
                    for a in qs
                    if args["query"].lower() in (a.title + " " + a.summary + " " + a.content).lower()
                ][:15]
            return list(qs)

        articles = await sync_to_async(_query)()
        if not articles:
            return {
                "success": True,
                "count": 0,
                "articles": [],
                "note": "No recently scraped articles in the user's saved news sources yet.",
            }
        return {
            "success": True,
            "count": len(articles),
            "articles": [
                {
                    "title": a.title,
                    "url": a.url,
                    "summary": a.summary or a.content[:300],
                    "image_url": getattr(a, "image_url", "") or "",
                    "source": a.feed.name,
                    "author": a.author,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                }
                for a in articles
            ],
        }
