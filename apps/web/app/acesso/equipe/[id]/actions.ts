"use server";
import { redirect } from "next/navigation";
import { acceptTeamInvitation } from "../../../../lib/bcos-api";
export async function acceptTeamInvitationAction(formData:FormData){const id=String(formData.get("invitation_id")??"").trim();if(!id) throw new Error("Convite inválido.");await acceptTeamInvitation(id);redirect("/acesso");}
