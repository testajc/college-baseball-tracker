import { Resend } from "resend";

const FROM_EMAIL = process.env.EMAIL_FROM || "College Baseball Tracker <onboarding@resend.dev>";

function getResend() {
  const key = process.env.RESEND_API_KEY;
  if (!key) throw new Error("RESEND_API_KEY is not configured");
  return new Resend(key);
}

export async function sendPortalAlert({
  userEmail,
  playerName,
  previousTeam,
  position,
  playerId,
}: {
  userEmail: string;
  playerName: string;
  previousTeam: string;
  position: string;
  playerId: number;
}) {
  const appUrl = process.env.NEXTAUTH_URL || "http://localhost:3000";

  const { error } = await getResend().emails.send({
    from: FROM_EMAIL,
    to: userEmail,
    subject: `${playerName} has entered the transfer portal`,
    html: `
      <div style="font-family: system-ui, sans-serif; max-width: 480px; margin: 0 auto;">
        <h2 style="color: #1e40af;">${playerName} is now in the transfer portal</h2>
        <table style="margin: 16px 0; font-size: 14px;">
          <tr><td style="padding: 4px 12px 4px 0; color: #666;">Team</td><td><strong>${previousTeam}</strong></td></tr>
          <tr><td style="padding: 4px 12px 4px 0; color: #666;">Position</td><td><strong>${position}</strong></td></tr>
        </table>
        <a href="${appUrl}/players/${playerId}"
           style="display: inline-block; background: #1e40af; color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 14px;">
          View Player Profile
        </a>
        <hr style="margin: 24px 0; border: none; border-top: 1px solid #e5e5e5;" />
        <p style="color: #999; font-size: 12px;">
          You received this because you favorited this player on College Baseball Tracker.
          <a href="${appUrl}/settings" style="color: #999;">Manage alert preferences</a>
        </p>
      </div>
    `,
  });

  if (error) {
    console.error("Failed to send portal alert email:", error);
    throw error;
  }
}
