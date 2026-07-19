// =============================================================================
// VeriField Nexus — Community Validation Page (Live Dynamic)
// =============================================================================

"use client";

import { useEffect, useState } from "react";
import { useToast } from "@/components/Toast";
import { 
  UsersRound, 
  CheckCircle2, 
  RefreshCw, 
  Clock, 
  Award,
  AlertTriangle,
  ThumbsUp,
  MessageSquare,
  Send
} from "lucide-react";
import { fetchCommunityFeed, upvoteCommunityPost, addCommunityComment } from "@/lib/api";
import type { CommunityFeedItem } from "@/lib/api";

export default function CommunityPage() {
  const toast = useToast();

  const [posts, setPosts] = useState<CommunityFeedItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Likes and comments state
  const [likedPosts, setLikedPosts] = useState<Record<string, boolean>>({});
  const [showComments, setShowComments] = useState<Record<string, boolean>>({});
  const [replyTexts, setReplyTexts] = useState<Record<string, string>>({});
  const [isSubmittingReply, setIsSubmittingReply] = useState<Record<string, boolean>>({});

  const loadFeed = async (showLoadingIndicator = true) => {
    if (showLoadingIndicator) setIsLoading(true);
    setError(null);
    try {
      const res = await fetchCommunityFeed(1, 50);
      setPosts(res.posts || []);
      setTotalCount(res.total || 0);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Failed to load community validations ledger.");
    } finally {
      if (showLoadingIndicator) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFeed(true);
    
    // Auto-refresh the community validation feed every 60 seconds for premium live synchronization
    const interval = setInterval(() => {
      loadFeed(false);
    }, 60000);
    
    return () => clearInterval(interval);
  }, []);

  // Compute stats dynamically from the live validations feed
  const approvedCount = posts.filter(p => p.response === "yes").length;
  const flaggedCount = posts.filter(p => p.response === "no").length;

  const handleUpvote = async (postId: string) => {
    // If already liked during this session, prevent double-voting
    if (likedPosts[postId]) return;

    // 1. Optimistic UI update for premium instant response
    setLikedPosts(prev => ({ ...prev, [postId]: true }));
    setPosts(prev => prev.map(p => p.id === postId ? { ...p, upvotes: p.upvotes + 1 } : p));

    try {
      await upvoteCommunityPost(postId);
      // Silent reload to make sure everything matches backend exactly
      loadFeed(false);
    } catch (err) {
      console.error("Upvote failed:", err);
      // Revert optimistic UI update on error
      setLikedPosts(prev => ({ ...prev, [postId]: false }));
      setPosts(prev => prev.map(p => p.id === postId ? { ...p, upvotes: Math.max(0, p.upvotes - 1) } : p));
    }
  };

  const handleToggleComments = (postId: string) => {
    setShowComments(prev => ({ ...prev, [postId]: !prev[postId] }));
  };

  const handleSubmitReply = async (postId: string) => {
    const text = replyTexts[postId]?.trim();
    if (!text) return;

    setIsSubmittingReply(prev => ({ ...prev, [postId]: true }));
    try {
      const newComment = await addCommunityComment(postId, text);
      
      // Clear input
      setReplyTexts(prev => ({ ...prev, [postId]: "" }));
      
      // Optimistically append comment to the post locally for instant response
      setPosts(prev => prev.map(p => {
        if (p.id === postId) {
          const currentComments = p.comments || [];
          return { ...p, comments: [...currentComments, newComment] };
        }
        return p;
      }));

      // Make sure comments drawer is expanded
      setShowComments(prev => ({ ...prev, [postId]: true }));
      
      // Silent reload to pull absolute source of truth
      loadFeed(false);
    } catch (err) {
      console.error("Reply failed:", err);
      toast.error('Operation Failed', "Failed to submit reply. Please verify connection.");
    } finally {
      setIsSubmittingReply(prev => ({ ...prev, [postId]: false }));
    }
  };

  return (
    <div className="space-y-6 animate-fade-in-up pb-10 text-[var(--color-text-primary)]">
      
      {/* 👑 TITLE SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#00B47A]/10 text-[#00B47A] text-[9px] font-extrabold tracking-wider uppercase border border-[#00B47A]/15">
              Social MRV Attribution
            </span>
            <span className="text-[10px] text-[var(--color-text-secondary)] font-semibold flex items-center gap-1">
              <CheckCircle2 size={11} className="text-[#00B47A]" /> Near Real-time Verification Feed
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)] mt-1 flex items-center gap-2">
            <UsersRound className="text-[#00B47A]" size={20} /> Community Peer Validation
          </h1>
          <p className="text-[var(--color-text-secondary)] text-xs mt-0.5">
            Audit peer-to-peer verification protocols, live validation responses, and agent reviews recorded on-chain.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-[10px] text-[var(--color-text-muted)] hidden sm:inline-flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] px-2.5 py-1 rounded-lg">
              <Clock size={11} className="text-[#00B47A]" /> Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button 
            onClick={() => loadFeed(true)} 
            className="p-2 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[#00B47A] hover:border-[#00B47A]/30 transition-all shadow-sm active:scale-95"
            title="Refresh Feed"
          >
            <RefreshCw size={16} className={isLoading ? "animate-spin text-[#00B47A]" : ""} />
          </button>
        </div>
      </div>

      {/* 📊 SUMMARY WIDGETS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">SMS Attestations & Votes</p>
            <p className="text-2xl font-black text-[var(--color-text-primary)] tracking-tight">
              {totalCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Recipient text confirmations</p>
          </div>
          <div className="p-3 bg-[#00B47A]/5 border border-[#00B47A]/10 rounded-xl text-[#00B47A] shrink-0">
            <Award size={18} />
          </div>
        </div>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Approved Audits</p>
            <p className="text-2xl font-black text-emerald-400 tracking-tight">
              {approvedCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Successfully verified assets</p>
          </div>
          <div className="p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-emerald-400 shrink-0">
            <CheckCircle2 size={18} />
          </div>
        </div>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-4 flex items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#00B47A]/30 transition-all">
          <div className="space-y-1">
            <p className="text-[9px] font-extrabold text-[var(--color-text-muted)] uppercase tracking-wider">Anomaly Flags</p>
            <p className="text-2xl font-black text-red-400 tracking-tight">
              {flaggedCount}
            </p>
            <p className="text-[9px] text-[var(--color-text-muted)] font-medium">Flagged by community review</p>
          </div>
          <div className="p-3 bg-red-500/5 border border-red-500/10 rounded-xl text-red-400 shrink-0">
            <AlertTriangle size={18} />
          </div>
        </div>
      </div>

      {/* 🧭 LIVE FEED GRIDS / EMPTY STATE */}
      {isLoading && posts.length === 0 ? (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center shadow-sm flex flex-col items-center justify-center">
          <div className="w-6 h-6 border-2 border-[#00B47A] border-t-transparent rounded-full animate-spin mb-3" />
          <span className="text-xs text-[var(--color-text-secondary)] font-semibold tracking-wide animate-pulse">Syncing Community Peer Ledger...</span>
        </div>
      ) : error ? (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-8 text-center shadow-sm max-w-md mx-auto">
          <AlertTriangle className="text-red-500 mx-auto mb-3" size={28} />
          <p className="text-red-400 text-xs font-semibold">{error}</p>
          <button onClick={() => loadFeed(true)} className="mt-4 px-4 py-1.5 rounded-xl bg-[#00B47A]/10 text-[#00B47A] text-xs font-bold border border-[#00B47A]/20 hover:bg-[#00B47A]/20 transition-all">
            Retry Sync
          </button>
        </div>
      ) : posts.length === 0 ? (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-12 text-center max-w-md mx-auto shadow-sm flex flex-col items-center justify-center">
          <div className="w-12 h-12 rounded-full bg-[#00B47A]/10 flex items-center justify-center mb-3 border border-[#00B47A]/15 text-[#00B47A]">
            <UsersRound size={22} />
          </div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">Roster Idle</h3>
          <p className="text-[var(--color-text-secondary)] text-xs mt-1 leading-relaxed">
            Beneficiaries are scheduled to receive SMS check-in requests. Validated peer logs will appear in this feed automatically.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in-up">
          {posts.map((post) => {
            const isApproved = post.response === "yes";
            const isFlagged = post.response === "no";
            const isLiked = likedPosts[post.id];
            const hasComments = post.comments && post.comments.length > 0;
            const commentsOpen = showComments[post.id] ?? false;

            return (
              <div 
                key={post.id}
                className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-5 shadow-sm hover:border-[#00B47A]/30 transition-all flex flex-col justify-between"
              >
                <div className="space-y-3">
                  {/* Header Row */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-[#00B47A]/10 border border-[#00B47A]/20 flex items-center justify-center text-[#00B47A] text-[10px] font-extrabold shrink-0">
                        {post.user_name ? post.user_name.substring(0, 2).toUpperCase() : "US"}
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <h4 className="text-xs font-bold text-[var(--color-text-primary)]">{post.user_name}</h4>
                          <span className="text-[8px] bg-[var(--color-background)] px-1.5 py-0.5 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] font-extrabold uppercase tracking-wider">
                            {post.user_role === "field_agent" ? "Field Agent" : post.user_role === "admin" ? "Admin" : "Member"}
                          </span>
                        </div>
                        <p className="text-[9px] text-[var(--color-text-muted)] font-semibold mt-0.5">
                          {post.action} • {new Date(post.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </p>
                      </div>
                    </div>

                    <span className={`px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-wider border shrink-0 ${
                      isApproved 
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/15" 
                        : isFlagged
                          ? "bg-red-500/10 text-red-400 border-red-500/15"
                          : "bg-[#00B47A]/10 text-[#00B47A] border-[#00B47A]/15"
                    }`}>
                      {isApproved ? "Approved" : isFlagged ? "Flagged" : "Review"}
                    </span>
                  </div>

                  {/* Body Content */}
                  <div className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-3">
                    <p className="text-xs text-[var(--color-text-primary)] font-medium leading-relaxed">
                      {post.content}
                    </p>
                    {post.property_name && (
                      <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-[var(--color-border)]/60 text-[9px] text-[var(--color-text-muted)] font-semibold uppercase">
                        <span>Asset:</span>
                        <span className="text-[#00B47A] truncate font-bold">{post.property_name}</span>
                        {post.property_type && (
                          <>
                            <span className="text-[var(--color-border)]">|</span>
                            <span>{post.property_type.replace(/_/g, ' ')}</span>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Sub-list of comments/replies */}
                {commentsOpen && (
                  <div className="mt-4 pt-3 border-t border-[var(--color-border)]/60 space-y-2.5">
                    {hasComments ? (
                      <div className="space-y-2 pl-3 border-l-2 border-[#00B47A]/30">
                        {post.comments.map((comment) => (
                          <div 
                            key={comment.id} 
                            className="bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl p-2.5 text-[11px]"
                          >
                            <div className="flex items-center justify-between gap-2 mb-0.5">
                              <div className="flex items-center gap-1.5">
                                <span className="font-bold text-[var(--color-text-primary)]">{comment.user_name}</span>
                                <span className="text-[7px] bg-[var(--color-surface)] px-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] font-bold uppercase scale-90">
                                  {comment.user_role === "field_agent" ? "Agent" : comment.user_role === "admin" ? "Admin" : "Member"}
                                </span>
                              </div>
                              <span className="text-[8px] text-[var(--color-text-muted)]">
                                {new Date(comment.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            <p className="text-[var(--color-text-secondary)] font-medium leading-relaxed">
                              {comment.comment}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[10px] text-[var(--color-text-muted)] italic pl-3">No replies yet. Be the first to start the thread!</p>
                    )}

                    {/* Inline input to type reply */}
                    <div className="flex gap-2 items-center pl-3">
                      <input 
                        type="text"
                        placeholder="Write a technical response..."
                        value={replyTexts[post.id] || ""}
                        onChange={(e) => setReplyTexts(prev => ({ ...prev, [post.id]: e.target.value }))}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !isSubmittingReply[post.id]) {
                            handleSubmitReply(post.id);
                          }
                        }}
                        className="flex-1 bg-[var(--color-background)] border border-[var(--color-border)] rounded-xl px-3 py-1.5 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-[#00B47A] transition-all"
                      />
                      <button 
                        disabled={!replyTexts[post.id]?.trim() || isSubmittingReply[post.id]}
                        onClick={() => handleSubmitReply(post.id)}
                        className="p-1.5 rounded-xl bg-[#00B47A] text-white disabled:opacity-40 hover:bg-[#009665] transition-all shadow-sm active:scale-95 shrink-0"
                      >
                        <Send size={12} />
                      </button>
                    </div>
                  </div>
                )}

                {/* Footer Engagement bar */}
                <div className="flex items-center justify-between border-t border-[var(--color-border)] pt-3 mt-4 text-[10px] text-[var(--color-text-muted)] font-bold">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => handleUpvote(post.id)}
                      className={`flex items-center gap-1.5 transition-colors ${
                        isLiked ? "text-[#00B47A]" : "hover:text-[#00B47A]"
                      }`}
                    >
                      <ThumbsUp size={12} className={isLiked ? "fill-[#00B47A]/10 text-[#00B47A]" : ""} />
                      <span>{post.upvotes || 0}</span>
                    </button>
                    <button 
                      onClick={() => handleToggleComments(post.id)}
                      className={`flex items-center gap-1.5 transition-colors hover:text-[#00B47A] ${
                        commentsOpen ? "text-[#00B47A]" : ""
                      }`}
                    >
                      <MessageSquare size={12} />
                      <span>
                        {hasComments 
                          ? `${post.comments.length} Repl${post.comments.length === 1 ? 'y' : 'ies'}`
                          : 'Reply'
                        }
                      </span>
                    </button>
                  </div>
                  <span className="text-[9px] font-extrabold tracking-wider text-[#00B47A]/90">
                    SECURED ATTACK IMMUNITY
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}
