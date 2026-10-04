import { requireTenantPermission } from "../../../lib/auth/authorization";
import Link from "next/link";

import { getAccessRoles, getTenantMembershipPermissions, getTenantMemberships, type TenantPermission } from "../../../lib/bcos-api";
import { assignUserRoleAction, inviteUserAction, removeUserAction, updateUserAction, updateUserPermissionsAction, updateUserStatusAction } from "./actions";

export const dynamic = "force-dynamic";

const roleLabel = { OWNER:"Proprietário", ADMIN:"Administrador", RECEPTION:"Recepção", PROFESSIONAL:"Profissional" } as const;
const statusLabel = { INVITED:"Convite pendente", ACTIVE:"Ativo", INACTIVE:"Bloqueado" } as const;
const permissionGroups:Array<{title:string;items:Array<{permission:TenantPermission;label:string}>}>=[
 {title:"Agenda",items:[{permission:"AGENDA_VIEW",label:"Visualizar"},{permission:"AGENDA_CREATE",label:"Criar"},{permission:"AGENDA_EDIT",label:"Editar"},{permission:"AGENDA_DELETE",label:"Excluir"},{permission:"AGENDA_MANAGE",label:"Gerenciar"}]},
 {title:"Disponibilidade e uso",items:[{permission:"AVAILABILITY_VIEW",label:"Visualizar disponibilidade"},{permission:"CHECKIN_VIEW",label:"Visualizar check-in e uso"},{permission:"CHECKIN_MANAGE",label:"Gerenciar check-in e uso"}]},
 {title:"Financeiro",items:[{permission:"FINANCE_VIEW",label:"Visualizar"},{permission:"FINANCE_CREATE",label:"Criar"},{permission:"FINANCE_EDIT",label:"Editar"},{permission:"FINANCE_DELETE",label:"Excluir"},{permission:"FINANCE_MANAGE",label:"Gerenciar"}]},
 {title:"Administração",items:[{permission:"ADMIN_VIEW",label:"Visualizar"},{permission:"ADMIN_CONFIG",label:"Editar configurações"},{permission:"USER_VIEW",label:"Visualizar usuários"},{permission:"USER_CREATE",label:"Criar/convidar usuário"},{permission:"USER_EDIT",label:"Editar usuário"},{permission:"USER_BLOCK",label:"Bloquear acesso"},{permission:"USER_DELETE",label:"Remover acesso"},{permission:"ROLE_MANAGE",label:"Gerenciar papel"},{permission:"USER_ADMIN",label:"Gerenciar acessos"}]},
 {title:"Outros",items:[{permission:"DASHBOARD_VIEW",label:"Visualizar visão geral"},{permission:"PROFESSIONAL_OWN",label:"Acessar o próprio portal profissional"}]},
];
