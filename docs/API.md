# API reference inventory

Base path: `/api/v1`. OpenAPI is served by FastAPI at `/docs` when documentation is enabled by deployment. Requests require `Authorization: Bearer <access_token>` unless marked otherwise. All resource access is scoped to the authenticated owner or authorized group membership/role.

## Auth, profile and sessions

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account; returns one-time recovery code |
| POST | `/auth/login` | Create authenticated session |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke current session |
| POST | `/auth/logout-all` | Revoke all user sessions |
| POST | `/auth/recovery/redeem` | Redeem single-use recovery code and replace password |
| POST | `/auth/delete-account` | Delete account after current password + `HAPUS AKUN` confirmation |
| GET / PATCH | `/me` | Get/update profile preferences (theme) |
| GET | `/sessions` | List current user's active sessions |
| GET | `/profiles/{profile_code}` | Lookup a public profile code; does not grant access |
| GET | `/export/data.json` | Export scoped personal data as JSON |

## Finance / reports

| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/accounts` | List/create accounts or wallets |
| PATCH | `/accounts/{account_id}` | Rename/archive/restore account; archive pauses linked active recurrence rules |
| GET / POST | `/categories` | List/create transaction categories |
| PATCH / DELETE | `/categories/{category_id}` | Edit/delete unused category; semantic type cannot be changed after references exist |
| GET / POST | `/transactions` | List/create confirmed income, expense or transfer |
| GET / PATCH / DELETE | `/transactions/{transaction_id}` | Read/edit/void own transaction |
| GET | `/reports/summary` | Income, expense, net cashflow, recorded balance and remaining budget |
| GET | `/reports/categories` | Expense totals by category |
| GET | `/reports/cashflow` | Income/expense series bucketed by local date |
| GET / POST | `/budgets` | List/create category budgets |
| PATCH / DELETE | `/budgets/{budget_id}` | Edit/delete a budget |
| GET / POST | `/goals` | List/create savings goals |
| PATCH / DELETE | `/goals/{goal_id}` | Edit/delete savings goal |
| GET / POST | `/recurring` | List/create recurring transaction rules |
| PATCH / DELETE | `/recurring/{rule_id}` | Pause/resume/update date/delete recurrence rule |
| POST | `/recurring/{rule_id}/run-now` | Materialize the next due transaction once |
| GET | `/export/transactions.csv` | Export confirmed transactions to CSV |

## Receipts / OCR

| Method | Path | Purpose |
|---|---|---|
| POST | `/receipts` | Validate/store JPG, PNG or PDF as a private draft |
| GET | `/receipts/{receipt_id}` | Read own receipt metadata and OCR draft |
| POST | `/receipts/{receipt_id}/extract` | Run local Tesseract OCR; returns suggested fields, extracted text and confidence average; does not create transaction |
| GET | `/receipts/{receipt_id}/download` | Download own uploaded document |
| POST | `/receipts/{receipt_id}/confirm` | Create transaction only after confirmation and valid fields |
| DELETE | `/receipts/{receipt_id}` | Delete own receipt and private file |

OCR requires Docker image dependencies Tesseract (`ind+eng`) and Poppler for PDFs. The initial parser provides suggestions only; OCR output is not authoritative and must be corrected/confirmed by user. OCR endpoint currently runs synchronously in the API process.

## Groups / messages / moderation

| Method | Path | Purpose |
|---|---|---|
| POST / GET | `/groups` | Create/list groups for current user |
| GET | `/groups/preview/{invite_code}` | Preview group from invite code |
| POST | `/groups/join-requests` | Request group membership |
| GET | `/groups/{group_id}/requests` | List pending requests (owner/admin) |
| POST | `/groups/{group_id}/requests/{request_id}/approve` | Approve membership |
| POST | `/groups/{group_id}/requests/{request_id}/reject` | Reject membership |
| GET | `/groups/{group_id}/members` | List group members (authorized member) |
| PATCH | `/groups/{group_id}` | Owner updates group details |
| POST | `/groups/{group_id}/invite/rotate` | Owner rotates/revokes invite code |
| PATCH / DELETE | `/groups/{group_id}/members/{user_id}` | Owner/admin role and membership control with role restrictions |
| GET / POST | `/groups/{group_id}/messages` | List/send group text messages |
| PATCH / DELETE | `/groups/{group_id}/messages/{message_id}` | Edit/delete own message (moderator deletion allowed by policy) |
| POST | `/groups/{group_id}/messages/{message_id}/reactions` | Add/update emoji reaction |
| POST | `/groups/{group_id}/messages/{message_id}/report` | Report a message |
| GET | `/groups/{group_id}/reports` | List group content reports (authorized moderator) |
| PATCH | `/groups/{group_id}/reports/{report_id}` | Update report status / moderator note |
| POST | `/groups/{group_id}/ws-ticket` | Mint one-use group-scoped ticket, 60-second expiry |
| WS | `/groups/{group_id}/ws?ticket=...` | Group message event channel; ticket only, not bearer token |
| POST / GET | `/users/{blocked_user_id}/block` / `/users/blocks` | Block/list blocked users |
| DELETE | `/users/{blocked_user_id}/block` | Unblock user |

WebSocket delivery is in-process only. Deploy one API instance; multi-instance fan-out requires Redis/pub-sub or managed realtime infrastructure.

## Investment journal / support

| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/watchlist` | List/add assets to a personal watchlist; no market quote provider configured |
| DELETE | `/watchlist/{item_id}` | Remove own watchlist item |
| GET / POST | `/investment/theses` | List/create personal investment thesis records |
| GET / POST | `/support/tickets` | List/create support tickets |

The current investment module is an educational journal/watchlist, not a broker or licensed advisory service. No live quote or news is fabricated. Voice/video rooms, trading execution and personal paid recommendations are not exposed as active APIs.

## Service and frontend

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Basic service health |
| GET | `/` | PWA shell |
| GET | `/assets/*` | Frontend static assets |
| GET | `/manifest.webmanifest` | PWA manifest |
| GET | `/sw.js` | Service worker |

API input schemas and exact response shape are best inspected in generated OpenAPI docs for the running build.
