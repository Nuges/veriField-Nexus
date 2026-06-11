import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { expect } from "chai";
import * as crypto from "crypto";

describe("verifield_nexus", () => {
  // Configure the client to use the local cluster.
  anchor.setProvider(anchor.AnchorProvider.env());

  // Workspace typing lookup
  const program = anchor.workspace.VerifieldNexus as Program<any>;
  const provider = anchor.getProvider();
  const authority = provider.wallet;

  it("anchors a mock MRV submission successfully!", async () => {
    // Generate a random 32-byte image hash
    const imageHash = crypto.randomBytes(32);
    
    // Derive the PDA for the verification record
    const [verificationRecordPda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("verification"), imageHash],
      program.programId
    );

    // Call the anchor_verification instruction
    const assetType = "cookstove";
    const latitude = new anchor.BN(4824167); // 4.824167 * 10^6 or 10^7
    const longitude = new anchor.BN(7030556);
    const timestamp = new anchor.BN(Math.floor(Date.now() / 1000));
    const trustScore = 95;

    await program.methods
      .anchorVerification(
        assetType,
        latitude,
        longitude,
        timestamp,
        Array.from(imageHash),
        trustScore
      )
      .accounts({
        verificationRecord: verificationRecordPda,
        authority: authority.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    // Fetch the account state and verify the values
    const record = await program.account.verificationRecordState.fetch(verificationRecordPda);
    
    expect(record.assetType).to.equal(assetType);
    expect(record.latitude.toString()).to.equal(latitude.toString());
    expect(record.longitude.toString()).to.equal(longitude.toString());
    expect(record.timestamp.toString()).to.equal(timestamp.toString());
    expect(Buffer.from(record.imageHash).toString("hex")).to.equal(imageHash.toString("hex"));
    expect(record.trustScore).to.equal(trustScore);
    expect(record.authority.toString()).to.equal(authority.publicKey.toString());
  });
});
