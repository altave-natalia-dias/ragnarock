"""
Ingest the WEB3 / smart-contract attack knowledge base into the RAG.

Standalone (adds ONLY the web3 chunks to the existing `pentest_kb` collection,
does NOT wipe MITRE / writeups):

    PYTHONPATH=/home/altave/.bughunter /home/altave/venv/bin/python3 -m rag.ingest.web3

Built from real, paid audit findings (Code4rena / Sherlock / Cyfrin / Pashov /
Cantina / OpenZeppelin / MixBytes / Shieldify / Quantstamp / Spearbit) + the
canonical DeFi bug-class taxonomy. Each chunk pairs a REUSABLE pattern with a
concrete disclosed example so retrieval returns both "what to look for" and
"where it was really paid".
"""
from __future__ import annotations
import sys
from pathlib import Path

RAG_DIR = Path(__file__).parent.parent

WEB3_KB: list[tuple[str, dict]] = []


def _kb(text: str, tags: list[str], category: str = "web3_smartcontract"):
    WEB3_KB.append((text.strip(), {
        "type":     "pentest_kb",
        "category": category,
        "tags":     ",".join(tags),
    }))


# ============================================================
# 0. PRE-DIVE TRIAGE  (decide if a target is worth auditing)
# ============================================================
_kb("""
WEB3 AUDIT — PRE-DIVE KILL / GO SIGNALS
Before reading code, decide if there is money here:
  KILL: TVL < ~$500K, unverified bytecode with no source, pure fork w/ no diff,
        owner can already rug by design (centralization = "acknowledged"), audited
        <30d ago by a top firm with all-fixed, honeypot tokenomics.
  GO:   novel accounting (shares<->assets), cross-contract callbacks, pluggable
        modules/managers, upgradeable proxies, multi-chain/bridge messaging,
        custom AMM/hook logic, signature/session schemes, reward/incentive math.
HIGH-VALUE AXES that repeatedly pay:
  1) shares<->assets conversion & rounding, 2) who-can-call (access control on
  CALLBACKS not just entrypoints), 3) external call re-entrancy into accounting,
  4) price/value read from a manipulable source, 5) first-deposit / empty-pool
  edge, 6) memory-vs-storage persistence, 7) signature replay / partial exec,
  8) front-run of one-time init/registration.
METHOD: read the invariant the code is trying to hold, then find one state where
it breaks. Write a Foundry PoC that asserts the broken invariant — a finding
without a passing PoC is a downgrade magnet.
""", ["web3", "audit", "methodology", "triage", "defi", "foundry"])


# ============================================================
# 1. ORACLE / VALUE MANIPULATION
# ============================================================
_kb("""
WEB3 BUG CLASS — ORACLE / BACKING-VALUE MANIPULATION (spot price is not a price)
Pattern: protocol reads the *value* of an asset/LP position from a source an
attacker can move in the same tx (DEX spot reserves, `getReserves()`, LP virtual
price on an imbalanced pool, `balanceOf` of a pool, an `additionalOwnedAssets()`
that resolves to an LP valuation). Attacker skews the source, makes the protocol
believe it has more collateral / more yield / higher share price, extracts, then
un-skews (sandwich).
Real: Aragon YieldManager (Cantina) — vault deposits into Curve 3pool;
`additionalOwnedAssets()` returns the LP position value. Attacker sells a lot of
the vault asset into the pool → protocol thinks the LP position is worth far more
→ believes surplus yield exceeds the safety buffer → sandwich `distributeYield()`
to mint excess shares (periphery manager can even front-run to swap the yield
distributor address and steal beyond excess). Ack'd: yield manager is trusted,
strategies limited to monotonic-share-price lending markets via governance.
Detect / grep: getReserves, latestAnswer w/o staleness, price0Cumulative,
`.balanceOf(pool)`, virtualPrice, get_virtual_price, `convertToAssets` on a live
pool, spot-based `quote`. Ask: can I move this within one tx / one block?
Fix: TWAP / Chainlink w/ heartbeat+deviation, monotonic share-price strategies,
value surplus vs an independent oracle, buffer > manipulable delta.
""", ["web3", "oracle", "price-manipulation", "defi", "curve", "sandwich", "flash-loan", "aragon"])

_kb("""
WEB3 BUG CLASS — FIRST-DEPOSIT / ERC4626 INFLATION (empty-pool share price)
Pattern: on an empty vault, shares = assets * totalSupply / totalAssets. Attacker
front-runs the first real depositor: mint 1 wei share, then DONATE (direct
transfer) a large amount to the vault so totalAssets >> totalSupply; victim's
deposit then rounds DOWN to 0 shares, attacker redeems and pockets the donation +
victim funds. The victim's `minMintAmount`/slippage guard is bypassed when the
entrypoint takes *token amounts* (not shares) and internal rounding yields 0.
Real: NUTS Finance SelfPeggingAsset (MixBytes, Critical) — mintShares rounds down
→ legitimate first minter gets 0 shares, attacker gets ~all. Recommendation:
mint dead shares (1000 wei) on first deposit / initialize paused w/ admin seed /
account for virtual shares+assets (OZ ERC4626 offset).
Detect: any `if (totalSupply==0)` mint branch, `shares = a*ts/ta`, deposits that
don't use internal accounting vs `balanceOf(this)`, missing virtual offset.
""", ["web3", "erc4626", "inflation", "first-deposit", "rounding", "vault", "defi"])


# ============================================================
# 2. ACCESS CONTROL — INCLUDING ON CALLBACKS
# ============================================================
_kb("""
WEB3 BUG CLASS — ACCESS CONTROL ON CALLBACKS / current-manager trust (swap attack)
Pattern: entrypoint validates `msg.sender == currentManager`, but the *callback*
that moves funds later re-reads `currentManager` and TRUSTS it to be the same
actor that created the request. A pool/config owner can (a) install a malicious
manager, (b) create a request that passes the entry check, (c) SWAP back to the
canonical manager, (d) trigger the callback which now uses the canonical manager
to move real user funds.
Real: Centrifuge V3 (Sherlock, H-1, many finders) — Spoke.request() checks the
current requestManager, but Spoke.requestCallback() re-uses requestManager[poolId]
without proving it created the request. Attacker: malicious manager creates a
fraudulent DepositRequest → swaps to AsyncRequestManager via hub.setRequestManager
→ approveDeposits() → AsyncRequestManager.approvedDeposits() moves ALL pending user
deposits from the shared globalEscrow into the attacker's pool escrow → withdraw.
Steals across ALL pools sharing the escrow. Fix: governance whitelist of
authorized managers, checked on BOTH request and callback; bind a request to the
manager that created it.
Detect: callbacks/`auth` fns that re-read a mutable role, shared escrow used by
many pools, setX manager/handler that can flip between request and settle.
""", ["web3", "access-control", "callback", "escrow", "centrifuge", "confused-deputy", "defi"])

_kb("""
WEB3 BUG CLASS — UNGUARDED / PUBLIC PRIVILEGED FUNCTION (mint, init, register)
Pattern: a function meant to be called by frontend/operator/admin is left
external with no modifier; attacker supplies bogus params → cascading corruption
of downstream accounting that reads those params later.
Real: Virtuals Protocol (Code4rena, H-04) — ContributionNft.mint is public
(only checks msg.sender == proposalProposer). Proposer supplies bogus
coreId/newTokenURI/parentId/isModel/datasetId → ServiceNft mint stores wrong core
& model, updateImpact overwrites another datasetId's impact, and getImpact feeds
AgentRewardV2._distributeContributorRewards & Minter.mint → higher/lower token
payouts, manipulated coreService. Fix: `require(msg.sender == _admin)` (a stray
comment "Admin can create proposal without votes" reveals intended gating).
Real: Subsquid tSQD (Pashov, H-04) — registerTokenOnL2() unrestricted; attacker
front-runs to set a wrong l2CustomTokenAddress → bridge permanently broken
(gateway mapping can't change). Fix: Ownable, onlyOwner on one-time registration.
Detect: external mint/initialize/register/setGateway with no onlyOwner/onlyRole,
one-time init not front-run-protected, "assumed the frontend calls this".
""", ["web3", "access-control", "public-mint", "initialization", "front-run", "bridge", "virtuals", "subsquid"])


# ============================================================
# 3. SIGNATURE / SESSION / NONCE
# ============================================================
_kb("""
WEB3 BUG CLASS — SIGNATURE VALIDATION BYPASS via disabled sub-check (flag left 0)
Pattern: a signature encodes optional feature flags; a nested/chained code path
lets an attacker leave a *security* flag unset so a validation branch is skipped,
leaving critical vars zero-valued and downstream `if (x != 0 && ...)` guards that
therefore never fire.
Real: Sequence v3 (Code4rena, H-01) — smart-wallet chained signature with the
checkpointer flag (bit 0x40) left 0. In BaseSig.recover the checkpointer-override
block is skipped → _checkpointer, snapshot.checkpoint, snapshot.imageHash all 0.
recoverChained runs with _ignoreCheckpointer=true; the final guard
`if (snapshot.imageHash != 0 && ... )` is skipped because imageHash==0 → an
EVICTED signer signs a payload valid against the STALE config and it passes.
Fix: if chained (flag 0x01) but checkpointer flag 0x40 unset → REVERT
(MissingCheckpointer). Lesson: any `if (flag && addr==0)` override + a later
`if (val != 0)` guard = look for the state where val stays 0 and the guard dies.
Detect: bitmask flags on signatures, `_ignore*` booleans, guards gated on
`!= bytes32(0)`, chained/aggregated signature recovery, stale-config snapshots.
""", ["web3", "signature", "auth-bypass", "wallet", "sequence", "session", "replay"])

_kb("""
WEB3 BUG CLASS — PARTIAL SIGNATURE REPLAY / FRONT-RUN (nonce consumed AFTER, or
revert-on-error leaves nonce unspent)
Pattern: a multi-call/batch is authorized by one signature. If a sub-call fails
under BEHAVIOR_REVERT_ON_ERROR the whole tx reverts INCLUDING nonce consumption →
the signature is still valid and can be replayed; and if nonce is consumed only
after validation, an attacker with mempool access can front-run a batch to run
only a chosen SUBSET of calls that were never meant to execute independently
(grief or extract value).
Real: Sequence v3 (Code4rena, H-02) — Calls.execute consumes nonce then validates;
session calls with REVERT_ON_ERROR let an attacker forge a valid partial signature
from a failed multi-call and execute a subset, or front-run to reorder/partial.
Fix: consume nonce atomically with successful full execution; bind the signature
to the exact ordered set of calls (all-or-nothing); disallow partial extraction.
Detect: _consumeNonce ordering vs signatureValidation vs _execute, per-call
behavior flags, batched intents, meta-tx relayers.
""", ["web3", "signature", "replay", "front-run", "nonce", "meta-tx", "sequence", "session"])


# ============================================================
# 4. REENTRANCY & STATE ORDERING
# ============================================================
_kb("""
WEB3 BUG CLASS — REENTRANCY THAT CORRUPTS ACCOUNTING (double-decrement via snapshot)
Not just "steal ETH" — reentrancy that runs while a balance-diff computation is
mid-flight desyncs internal accounting from real balances → frozen funds, wrong
share price, cascading liquidations.
Real: Notional v4 AbstractYieldStrategy.redeemNative (MixBytes, Critical) —
_burnShares snapshots yieldTokensBefore, then does an external swap; a MALICIOUS
ERC20 on the Uniswap-V2 path reenters via ILendingRouter.initiateWithdraw() (not
all router/manager entrypoints are nonReentrant). The request manager pulls N
yield tokens (lowering real balance AND s_yieldTokenBalance) mid-burn; control
returns and _burnShares computes redeemed = before-after and subtracts again →
s_yieldTokenBalance reduced twice by N → N tokens unaccounted & frozen, price
distorted, health factors drop → liquidations → repeat. Fix: nonReentrant on ALL
entrypoints reachable during redemption (initiateWithdraw/finalize included);
restrict swap path to single-hop (exactly 2 tokens) so no attacker token can sit
mid-path; update accounting before external calls (CEI).
Detect: balanceOf-before / balanceOf-after diffs around an external call,
user-supplied swap paths / arbitrary tokens in a route, callbacks (ERC777
tokensReceived, ERC721/1155 hooks, flash-loan callbacks, swap `transfer`),
missing nonReentrant on secondary routers/managers.
""", ["web3", "reentrancy", "accounting-desync", "notional", "cei", "vault", "defi"])

_kb("""
WEB3 BUG CLASS — MEMORY vs STORAGE (mutation not persisted → broken invariants)
Pattern: a struct is passed as `memory`, mutated, and the caller expects the
change to persist — but it never hits storage. Silent divergence of on-chain
state from intended state; classic for linked lists, orderbooks, accounting maps.
Real: GTE CLOB Book.sol (Code4rena, H-01) — addOrderToBook passes `Order memory
order`; _updateLimitPostOrder sets `order.prevOrderId = tailOrder.id` on the MEMORY
copy → never stored. On removal, `prev = order.prevOrderId` is null → the
double-linked list unlinks wrong: head/tail pointers corrupt; when the book is
full and the tail order becomes invalid → DoS of order add/remove. Fix: operate on
`storage` refs (self.orders[order.id].prevOrderId = ...), or write back.
Detect: `Foo memory x` that is mutated after being read from a mapping, linked-list
prev/next updates, `struct memory` returned/passed then expected persistent.
""", ["web3", "storage", "memory", "linked-list", "orderbook", "dos", "gte", "solidity"])


# ============================================================
# 5. ARITHMETIC / ACCOUNTING / ROUNDING
# ============================================================
_kb("""
WEB3 BUG CLASS — ROUNDING DIRECTION, CEIL/FLOOR & SELF-IN-LIST (DoS / drain)
Pattern: ceil vs floor chosen wrong, or an actor is included in a list it iterates
over its own share of → an intermediate sum exceeds the whole → underflow on
`whole - sum` → permanent DoS; or rounding always favors the user → slow drain.
Real: Terplayer BvtRewardVault.withdraw (Shieldify, Critical) — withdraw iterates
delegated stakes using CEIL division AND includes the user in their own delegation
list → totalDelegatedAmount > amount → `remainingAmount = amount - totalDelegatedAmount`
underflows (reverts) → ALL withdrawals fail, funds permanently locked. Fix:
exclude self, use floor division, assign remainder explicitly.
Real: LoopVaults _vestingInterest (Pashov, H-01) — formula inverted:
`(now-lastUpdate)*vI/duration` returns 0 at update and GROWS, so totalAssets()
includes all accrued interest right after an update → MEV-able. Fix:
`(duration-(now-lastUpdate))*vI/duration`.
Detect: `+ x - 1) / y` ceil idioms, `<= 0` on unsigned (Remora: numTokens<=0 on
uint is always-false/misleading), a - b where b is a summed loop, vesting/streaming
math, "user in users[]" loops.
""", ["web3", "arithmetic", "rounding", "underflow", "dos", "vesting", "mev", "terplayer", "loopvaults"])

_kb("""
WEB3 BUG CLASS — STALE / UNUPDATED ACCUMULATOR (refund & burn desync)
Pattern: a running total (shares minted, pending deposits, debt) is used in a
per-item calculation but is NOT decremented as items are processed → later items
over/under-count; or a burn/settlement loop skips some items without asserting the
target reached zero → ERC1155/ERC20 balance diverges from internal group arrays.
Real: Neutral Trade refund_deposit (Quantstamp) — shares_to_revert uses
last_total_shares_minted which is never reduced after each refund → successive
refunds cancel too many shares → correct underlying balance but under-reported
total_shares, distorted price (compounds with process_deposits reuse). Fix:
decrement last_total_shares_minted by shares_to_revert each refund.
Real: Radius EVMAuth _burnGroupBalances (Trail-of-Bits-style) — loop skips EXPIRED
token groups and never checks `debt == 0` at the end → burn silently incomplete →
ERC1155 balance says N burned but group arrays only removed M<N → desync. Fix:
`require(debt == 0)` after the loop; test mixed valid/expired burns.
Detect: cumulative_* / total_* used in a divisor/multiplier but not updated in the
same loop, burn/settle loops with `continue` and no completion assertion.
""", ["web3", "accounting-desync", "refund", "burn", "erc1155", "neutral-trade", "evmauth"])


# ============================================================
# 6. AMM / HOOK / MEV & INCENTIVE DESIGN
# ============================================================
_kb("""
WEB3 BUG CLASS — HOOK BACK-RUN / JIT LP FEE FARMING (Uniswap v4 hooks & stakers)
Pattern: a hook auto-executes a swap (e.g. to restore a peg) that pays LP fees;
or fees are split by liquidity-SHARE at claim/fill time regardless of how long
liquidity was present. A dominant / just-in-time LP mines fees with ~no price risk
and can redeem principal ~1:1, extracting value repeatedly.
Real: Licredity _afterSwap (Cyfrin) — when price <= 1 the hook back-runs a swap to
push price up, paying fees to LPs. Attacker owns most liquidity around price 1:
push price just under 1 (earn fee leg), trigger back-run (earn again), redeem via
exchangeFungible ~1:1 → keeps both fee legs, loops. Fix: revert swaps that end
below peg / reject sqrtPriceLimit below 1; don't accrue fees when sender==self
(dynamic fee 0 for the hook's own back-run); whitelist LPs below peg.
Real: OpenZeppelin Uniswap Hooks LimitOrderHook (OZ audit) & Ouroboros
UniswapV3Staker (Pashov, H-01) — fees/rewards distributed by share-at-fill with no
time-weighting → JIT LP adds 90% liquidity right before fill, withdraws, captures
fees accrued before it ever participated; full-range-only incentive design also
kills real staker participation. Fix: per-user fee snapshots / timestamp so only
fees accrued AFTER a position was active are claimable.
Detect: afterSwap/beforeSwap that itself swaps, fee split == liquidityShare with no
time factor, `sender == address(this)` not special-cased, JIT add/remove in one
block, fixed-range incentives.
""", ["web3", "amm", "uniswap-v4", "hook", "jit", "mev", "fee-farming", "licredity", "openzeppelin"])


# ============================================================
# 7. CROSS-CUTTING CHECKLIST + FOUNDRY POC
# ============================================================
_kb("""
WEB3 — 12-CLASS AUDIT CHECKLIST (run against every contract)
1) Accounting desync: internal var vs real balanceOf after every external call.
2) Access control: entrypoints AND callbacks; roles that can flip mid-flow.
3) Incomplete path / early-return / continue without invariant assert.
4) Off-by-one & rounding direction (favor the protocol, never the caller).
5) Oracle/value from a same-tx-manipulable source (spot, LP vprice, balanceOf).
6) ERC4626 first-deposit inflation / virtual shares offset.
7) Reentrancy (ERC777/721/1155 hooks, flash-loan cb, swap transfer, secondary routers).
8) Flash-loan amplification of any of the above (no capital constraint on attacker).
9) Signature replay / partial exec / nonce ordering / chained-flag bypass.
10) Proxy/upgrade: uninitialized impl, storage-collision, missing __gap, selfdestruct.
11) Front-run of one-time init/register/first-mint (& sandwich of value reads).
12) Memory-vs-storage persistence; stale accumulators not decremented in-loop.
INVARIANTS to assert in PoC: sum(userShares)==totalSupply; internalBal==token.balanceOf;
no path mints/withdraws more than deposited; price monotonic where claimed;
signature usable exactly once for exactly the intended calls.
""", ["web3", "checklist", "audit", "defi", "invariant"])

_kb("""
WEB3 — FOUNDRY POC SKELETON (proof beats prose; unproven finding = downgrade)
    // forge test --match-test test_PoC -vvv   (fork if oracle/DEX needed:
    //   forge test --fork-url $RPC --match-test test_PoC)
    function test_PoC_<class>() external {
        // 1. setup victim state (legit deposit into shared escrow/vault)
        // 2. attacker action (malicious manager / donate 1 wei / reenter / swap-skew)
        // 3. trigger the flawed path (callback / redeem / distributeYield / withdraw)
        // 4. assert the BROKEN invariant, e.g.:
        assertLt(token.balanceOf(address(vault)), internalAccounting, "funds frozen");
        assertEq(globalEscrowBefore - globalEscrowAfter, stolen, "cross-pool theft");
        assertGe(weight, threshold, "evicted signer passed");
    }
Tips: use vm.mockCall for oracles/checkpointers; MaliciousToken.transfer() to
reenter; addLiquidity to skew a Curve/UniV2 pool; `forge-config: default.isolate`
for per-call gas/nonce realism. Report: title = impact-first, CVSS/severity,
root-cause line link, minimal PoC, fix diff. Immunefi/C4/Sherlock reward the PoC.
""", ["web3", "foundry", "poc", "report", "immunefi", "code4rena", "sherlock"])


def ingest_web3(rag=None):
    from rag.store import get_rag
    r = rag or get_rag()
    print(f"  Upserting {len(WEB3_KB)} web3 smart-contract KB records → pentest_kb …")
    r.upsert_batch("pentest_kb", WEB3_KB)
    print("  Web3 smart-contract knowledge ingested.")


if __name__ == "__main__":
    sys.path.insert(0, str(RAG_DIR.parent))
    ingest_web3()
    print("Done.")
