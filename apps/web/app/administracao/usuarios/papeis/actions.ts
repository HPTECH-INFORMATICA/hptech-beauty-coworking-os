"use server";
import { revalidatePath } from "next/cache";
import { createAccessRole, deleteAccessRole, getAccessRolePermissionCatalog, updateAccessRole } from "../../../../lib/bcos-api";

const value=(f:FormData,k:string)=>String(f.get(k)??"").trim();
async function selectedPermissions(formData:FormData){
 const catalog=await getAccessRolePermissionCatalog();
 return catalog.filter(item=>formData.get("permission:"+item.code)==="on").map(item=>item.code);
}
export async function createRoleAction(formData:FormData){
 const name=value(formData,"name"); if(!name) throw new Error("Nome do papel é obrigatório.");
 await createAccessRole({name,description:value(formData,"description"),permissions:await selectedPermissions(formData)});
 revalidatePath("/administracao/usuarios"); revalidatePath("/administracao/usuarios/papeis");
}
export async function updateRoleAction(formData:FormData){
 await updateAccessRole(value(formData,"role_id"),{name:value(formData,"name"),description:value(formData,"description"),active:formData.get("active")==="on",permissions:await selectedPermissions(formData)});
 revalidatePath("/administracao/usuarios"); revalidatePath("/administracao/usuarios/papeis");
}
export async function deleteRoleAction(formData:FormData){
 await deleteAccessRole(value(formData,"role_id")); revalidatePath("/administracao/usuarios/papeis");
}
