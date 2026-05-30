<template>
  <div>
    <h1 class="page-title">项目管理</h1>
    <div class="toolbar">
      <el-button v-if="auth.canEdit" type="primary" @click="openCreate">新建项目</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="projects" stripe>
      <el-table-column prop="name" label="项目名称" />
      <el-table-column prop="code" label="项目编码" width="180" />
      <el-table-column prop="description" label="说明" />
      <el-table-column prop="created_at" label="创建时间" width="210" />
      <el-table-column label="操作" width="250" class-name="table-actions-cell">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button v-if="canManageProject(row)" text type="primary" @click="edit(row)">编辑</el-button>
            <el-button text type="primary" @click="openMembers(row)">成员</el-button>
            <el-button v-if="canDeleteProject(row)" text type="danger" @click="remove(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑项目' : '新建项目'" width="520px" @closed="resetForm">
      <el-form label-position="top">
        <el-form-item label="项目名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="项目编码">
          <el-input v-model="form.code" :disabled="Boolean(editingId)" placeholder="例如 UAV-DOC-001" />
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialog">取消</el-button>
        <el-button type="primary" @click="save">{{ editingId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="membersDialog" :title="membersTitle" width="760px" @closed="resetMemberForm">
      <el-form v-if="canManageSelectedMembers" class="member-form" label-position="top">
        <el-form-item label="用户">
          <el-select v-model="memberForm.user_id" filterable placeholder="选择启用中的用户" @change="handleMemberUserChange">
            <el-option
              v-for="user in availableUsers"
              :key="user.id"
              :label="`${user.username}${user.full_name ? ` (${user.full_name})` : ''}`"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="项目角色">
          <el-select v-model="memberForm.role">
            <el-option label="管理者" value="manager" :disabled="!canAssignProjectRole(memberForm.user_id, 'manager')" />
            <el-option label="编辑者" value="editor" :disabled="!canAssignProjectRole(memberForm.user_id, 'editor')" />
            <el-option label="查看者" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item class="member-add">
          <el-button type="primary" @click="addMember">添加成员</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="members" stripe>
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="full_name" label="姓名" width="140" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column label="项目角色" width="170">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'owner'" type="warning">负责人</el-tag>
            <el-select v-else v-model="row.role" size="small" :disabled="!canManageSelectedMembers" @change="updateMember(row)">
              <el-option label="管理者" value="manager" :disabled="!canAssignMemberRole(row, 'manager')" />
              <el-option label="编辑者" value="editor" :disabled="!canAssignMemberRole(row, 'editor')" />
              <el-option label="查看者" value="viewer" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" class-name="table-actions-cell">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-if="row.role !== 'owner' && canManageSelectedMembers" text type="danger" @click="removeMember(row)">移除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiError } from '@/api/http'
import { authApi, projectApi, type Project, type ProjectMember, type User } from '@/api'
import { useAuthStore } from '@/stores/auth'

type EditableProjectRole = 'manager' | 'editor' | 'viewer'

const projects = ref<Project[]>([])
const users = ref<User[]>([])
const members = ref<ProjectMember[]>([])
const dialog = ref(false)
const membersDialog = ref(false)
const editingId = ref<number>()
const selectedProject = ref<Project>()
const form = reactive({ name: '', code: '', description: '' })
const memberForm = reactive<{ user_id?: number; role: EditableProjectRole }>({ user_id: undefined, role: 'viewer' })
const auth = useAuthStore()

const membersTitle = computed(() => (selectedProject.value ? `项目成员：${selectedProject.value.name}` : '项目成员'))
const availableUsers = computed(() => {
  const memberUserIds = new Set(members.value.map((item) => item.user_id))
  return users.value.filter((user) => !memberUserIds.has(user.id))
})
const currentProjectMember = computed(() => members.value.find((item) => item.user_id === auth.user?.id))
const canManageSelectedMembers = computed(() => {
  if (!selectedProject.value || !auth.user) return false
  return auth.isAdmin || selectedProject.value.owner_id === auth.user.id || currentProjectMember.value?.role === 'manager'
})

// 加载页面所需的基础数据。
async function load() {
  projects.value = await projectApi.list()
}

// 打开新建表单弹窗。
function openCreate() {
  resetForm()
  dialog.value = true
}

// 打开编辑弹窗并回填数据。
function edit(project: Project) {
  if (!canManageProject(project)) return
  editingId.value = project.id
  Object.assign(form, {
    name: project.name,
    code: project.code,
    description: project.description || '',
  })
  dialog.value = true
}

// 重置表单到初始状态。
function resetForm() {
  editingId.value = undefined
  Object.assign(form, { name: '', code: '', description: '' })
}

// 关闭当前表单弹窗。
function cancelDialog() {
  dialog.value = false
}

// 保存当前表单数据。
async function save() {
  try {
    if (editingId.value) {
      await projectApi.update(editingId.value, { name: form.name, description: form.description })
      ElMessage.success('项目已更新')
    } else {
      await projectApi.create(form)
      ElMessage.success('项目创建成功')
    }
    dialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(apiError(error, '保存失败'))
  }
}

// 删除指定记录并刷新列表。
async function remove(project: Project) {
  if (!canDeleteProject(project)) return
  try {
    await ElMessageBox.confirm(
      `删除项目“${project.name}”会同时删除其模型、模板和生成文档，是否继续？`,
      '确认删除',
      { type: 'warning' },
    )
    await projectApi.remove(project.id)
    ElMessage.success('项目已删除')
    await load()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '删除失败'))
    }
  }
}

// 处理 openMembers 相关逻辑。
async function openMembers(project: Project) {
  selectedProject.value = project
  membersDialog.value = true
  resetMemberForm()
  await Promise.all([loadMembers(project.id), loadUserOptions()])
}

// 处理 loadMembers 相关逻辑。
async function loadMembers(projectId: number) {
  members.value = await projectApi.members(projectId)
}

// 处理 loadUserOptions 相关逻辑。
async function loadUserOptions() {
  users.value = await authApi.userOptions()
}

// 处理 resetMemberForm 相关逻辑。
function resetMemberForm() {
  Object.assign(memberForm, { user_id: undefined, role: 'viewer' as EditableProjectRole })
}

// 处理 canManageProject 相关逻辑。
function canManageProject(project: Project) {
  if (!auth.user) return false
  return auth.isAdmin || project.owner_id === auth.user.id
}

// 处理 canDeleteProject 相关逻辑。
function canDeleteProject(project: Project) {
  if (!auth.user) return false
  return auth.isAdmin || project.owner_id === auth.user.id
}

// 处理 userById 相关逻辑。
function userById(userId?: number) {
  return users.value.find((user) => user.id === userId)
}

// 处理 memberUser 相关逻辑。
function memberUser(member: ProjectMember) {
  return users.value.find((user) => user.id === member.user_id)
}

// 处理 canAssignProjectRole 相关逻辑。
function canAssignProjectRole(userId: number | undefined, role: EditableProjectRole) {
  const user = userById(userId)
  if (!user) return role === 'viewer'
  if (user.role === 'reader') return role === 'viewer'
  return role === 'manager' || role === 'editor' || role === 'viewer'
}

// 处理 canAssignMemberRole 相关逻辑。
function canAssignMemberRole(member: ProjectMember, role: EditableProjectRole) {
  const user = memberUser(member)
  if (!user) return role === 'viewer'
  if (user.role === 'reader') return role === 'viewer'
  return role === 'manager' || role === 'editor' || role === 'viewer'
}

// 处理 handleMemberUserChange 相关逻辑。
function handleMemberUserChange() {
  if (!canAssignProjectRole(memberForm.user_id, memberForm.role)) {
    memberForm.role = 'viewer'
  }
}

// 处理 addMember 相关逻辑。
async function addMember() {
  if (!canManageSelectedMembers.value) return
  if (!selectedProject.value || !memberForm.user_id) {
    ElMessage.warning('请先选择用户')
    return
  }
  try {
    await projectApi.addMember(selectedProject.value.id, {
      user_id: memberForm.user_id,
      role: memberForm.role,
    })
    ElMessage.success('成员已添加')
    resetMemberForm()
    await loadMembers(selectedProject.value.id)
  } catch (error) {
    ElMessage.error(apiError(error, '添加成员失败'))
  }
}

// 处理 updateMember 相关逻辑。
async function updateMember(member: ProjectMember) {
  if (!canManageSelectedMembers.value) return
  if (!selectedProject.value || member.role === 'owner') return
  if (!canAssignMemberRole(member, member.role as EditableProjectRole)) {
    ElMessage.warning('该用户全局角色不允许授予此项目角色')
    await loadMembers(selectedProject.value.id)
    return
  }
  try {
    const updated = await projectApi.updateMember(selectedProject.value.id, member.id, { role: member.role })
    const index = members.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) members.value[index] = updated
    ElMessage.success('成员已更新')
  } catch (error) {
    ElMessage.error(apiError(error, '更新成员失败'))
    await loadMembers(selectedProject.value.id)
  }
}

// 处理 removeMember 相关逻辑。
async function removeMember(member: ProjectMember) {
  if (!canManageSelectedMembers.value) return
  if (!selectedProject.value) return
  try {
    await ElMessageBox.confirm(`从项目中移除“${member.username}”？`, '确认移除', { type: 'warning' })
    await projectApi.removeMember(selectedProject.value.id, member.id)
    ElMessage.success('成员已移除')
    await loadMembers(selectedProject.value.id)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(apiError(error, '移除成员失败'))
    }
  }
}

onMounted(load)
</script>

<style scoped>
.member-form {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 180px auto;
  gap: 12px;
  align-items: end;
  margin-bottom: 16px;
}
.member-form :deep(.el-select) {
  width: 100%;
}
.member-add {
  margin-bottom: 18px;
}
@media (max-width: 760px) {
  .member-form {
    grid-template-columns: 1fr;
  }
  .member-add {
    margin-bottom: 0;
  }
}
</style>
