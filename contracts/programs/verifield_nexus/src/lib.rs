/**
 * =============================================================================
 * VeriField Nexus — Solana Anchor Program (On-Chain State Ledger)
 * =============================================================================
 */

use anchor_lang::prelude::*;

declare_id!("Fg6PaFsp7w5ybzGqGL3qcTi24CjOQERAJ29fkc29fkc");

#[program]
pub mod verifield_nexus {
    use super::*;

    /**
     * Anchors a trust-scored environmental verification record on-chain.
     * Logs coordinates, timestamp, Trust Engine score, and cryptographic proof hash.
     */
    pub fn anchor_verification(
        ctx: Context<AnchorVerification>,
        asset_type: String,
        latitude: i64,      // Multiplied by 10^7 for decimal precision
        longitude: i64,     // Multiplied by 10^7 for decimal precision
        timestamp: u64,
        image_hash: [u8; 32], // 32-byte binary representation of SHA-256 hash
        trust_score: u8,
    ) -> Result<()> {
        let record = &mut ctx.accounts.verification_record;
        
        record.authority = ctx.accounts.authority.key();
        record.asset_type = asset_type;
        record.latitude = latitude;
        record.longitude = longitude;
        record.timestamp = timestamp;
        record.image_hash = image_hash;
        record.trust_score = trust_score;
        record.bump = ctx.bumps.verification_record;

        // Emit an event to enable indexers and DePIN climate dApps to listen to verification entries
        emit!(VerificationEvent {
            verification_id: record.key(),
            authority: record.authority,
            image_hash,
            trust_score,
        });

        Ok(())
    }
}

/**
 * Account context for verification anchor instruction.
 */
#[derive(Accounts)]
#[instruction(
    asset_type: String,
    latitude: i64,
    longitude: i64,
    timestamp: u64,
    image_hash: [u8; 32],
    trust_score: u8
)]
pub struct AnchorVerification<'info> {
    // PDA representing the individual verification record
    #[account(
        init,
        payer = authority,
        space = 8 + 32 + (4 + 32) + 8 + 8 + 8 + 32 + 1 + 1, // Anchor discriminator + fields + string buffer
        seeds = [b"verification", image_hash.as_ref()],
        bump
    )]
    pub verification_record: Account<'info, VerificationRecordState>,
    
    #[account(mut)]
    pub authority: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

/**
 * On-chain state storage account representing a verified climate asset.
 */
#[account]
pub struct VerificationRecordState {
    pub authority: Pubkey,      // Authorised Verification Engine validator key
    pub asset_type: String,     // category name
    pub latitude: i64,          // Latitude scaled
    pub longitude: i64,         // Longitude scaled
    pub timestamp: u64,         // Unix epoch
    pub image_hash: [u8; 32],   // SHA-256 binary hash
    pub trust_score: u8,        // 0-100 calculated score
    pub bump: u8,               // PDA bump seed
}

/**
 * Transaction log event emitted on-chain.
 */
#[event]
pub struct VerificationEvent {
    pub verification_id: Pubkey,
    pub authority: Pubkey,
    pub image_hash: [u8; 32],
    pub trust_score: u8,
}
