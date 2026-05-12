<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>主数据管理</h3>
        <span>管理核算组织、单位、银行账户等基础数据</span>
      </div>

      <!-- 子标签页 -->
      <div class="tabs-bar">
        <NButton class="tab-btn" :class="{ active: activeTab === 'accounts' }" quaternary @click="activeTab = 'accounts'">账户列表</NButton>
        <NButton class="tab-btn" :class="{ active: activeTab === 'divisions' }" quaternary @click="activeTab = 'divisions'">核算管理</NButton>
        <NButton class="tab-btn" :class="{ active: activeTab === 'entities' }" quaternary @click="activeTab = 'entities'">单位管理</NButton>
        <NButton class="tab-btn" :class="{ active: activeTab === 'banks' }" quaternary @click="activeTab = 'banks'">账户管理</NButton>
      </div>

      <!-- ==================== 标签页1: 账户列表 ==================== -->
      <div v-show="activeTab === 'accounts'">
        <div class="filters-bar filters-bar-dense">
          <NSelect v-model:value="filterDivision" :options="divisionFilterOptions" placeholder="全部核算组织" clearable @update:value="loadAccounts" />
          <NSelect v-model:value="filterEntity" :options="entityFilterSelectOptions" placeholder="全部单位" clearable />
          <input v-model="keyword" class="filter" placeholder="搜索账户编号/名称/银行/账号" style="width:220px" />
          <NSelect v-model:value="filterStatus" :options="STATUS_FILTER_OPTIONS" style="width:90px" />
          <div class="filter-spacer"></div>
          <div class="btn-row">
            <div class="dropdown" :class="{ open: accDropdownOpen }" v-if="selectedAccountIds.length > 0">
              <NButton secondary @click="accDropdownOpen = !accDropdownOpen">批量操作 ({{ selectedAccountIds.length }})</NButton>
              <div class="dropdown-menu">
                <NButton quaternary @click="batchAccounts('enable'); accDropdownOpen = false">批量启用</NButton>
                <NButton quaternary @click="batchAccounts('disable'); accDropdownOpen = false">批量停用</NButton>
                <NButton quaternary @click="batchAccounts('delete'); accDropdownOpen = false" class="dropdown-item-danger">批量删除</NButton>
              </div>
            </div>
            <NButton secondary @click="downloadTemplate">下载导入模板</NButton>
            <NButton secondary @click="triggerImport">批量导入</NButton>
            <input ref="importInput" type="file" accept=".xls,.xlsx" style="display:none" @change="doImport" />
            <NButton type="primary" @click="openAccountForm()">+ 新建账户</NButton>
          </div>
        </div>

        <!-- 无数据时：不显示任何表格 -->
        <div v-if="!filteredAccounts.length" style="text-align:center;color:var(--muted);padding:40px 0">
          暂无账户数据，请下载导入模板并批量导入
        </div>
        <!-- 有数据时：动态列表格 -->
        <template v-else>
        <div class="table-wrap table-wrap-wide">
          <table>
            <thead>
              <tr>
                <th class="col-ck"><input type="checkbox" :checked="isAllAccountsSelected" @change="toggleAllAccounts" /></th>
                <th v-for="col in activeAccountColumns" :key="col.key">{{ col.label }}</th>
                <th class="col-action">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in filteredAccounts" :key="a.id"
                  :class="{ disabled: a.status === 'disabled', selected: selectedAccountIds.includes(a.id) }"
                  @dblclick="openAccountForm(a)">
                <td class="col-ck"><input type="checkbox" :value="a.id" v-model="selectedAccountIds" /></td>
                <td v-for="col in activeAccountColumns" :key="col.key" :class="col.type === 'money' ? 'money' : (col.type === 'code' || col.type === 'text' && (col.key === 'account_number' || col.key === 'account_last_four') ? 'mono' : '')">
                  <template v-if="col.type === 'bool'">
                    <span :class="getBoolVal(a, col.key) ? 'bool-yes' : 'bool-no'">{{ getBoolVal(a, col.key) ? '是' : '否' }}</span>
                  </template>
                  <span v-else-if="col.type === 'tag'" class="tag" :class="col.key === 'account_type' ? 'tag-blue' : 'tag-gray'">{{ a[col.key] || '-' }}</span>
                  <span v-else-if="col.type === 'status'" class="tag" :class="a.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ a.status === 'enabled' ? '启用' : '停用' }}</span>
                  <template v-else-if="col.type === 'money'">{{ fmtMoney(a[col.key]) }}</template>
                  <strong v-else-if="col.type === 'code'">{{ a[col.key] }}</strong>
                  <template v-else-if="col.type === 'input_method'">{{ a.input_method === 'bank_import' ? '银行导入' : (a.input_method === 'manual' ? '手工填写' : (a.input_method || '手工填写')) }}</template>
                  <template v-else>{{ a[col.key] || '-' }}</template>
                </td>
                <td class="action-cell">
                  <NButton secondary size="small" @click="openAccountForm(a)">编辑</NButton>
                  <NButton secondary size="small" v-if="a.status==='enabled'" @click="toggleAccountStatus(a, 'disabled')">停用</NButton>
                  <NButton secondary size="small" v-else @click="toggleAccountStatus(a, 'enabled')">启用</NButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="bottom-bar">
          <span class="count-info">共 {{ filteredAccounts.length }} 条记录</span>
        </div>
        </template>
      </div>

      <!-- ==================== 标签页2: 核算管理 ==================== -->
      <div v-show="activeTab === 'divisions'">
        <div class="filters-bar">
          <NSelect v-model:value="divFilterStatus" :options="STATUS_FILTER_OPTIONS_2" style="width:110px" />
          <div class="filter-spacer"></div>
          <div class="btn-row">
            <div class="dropdown" :class="{ open: divDropdownOpen }" v-if="selectedDivIds.length > 0">
              <NButton secondary @click="divDropdownOpen = !divDropdownOpen">批量操作 ({{ selectedDivIds.length }})</NButton>
              <div class="dropdown-menu">
                <NButton quaternary @click="batchDivisions('enable'); divDropdownOpen = false">批量启用</NButton>
                <NButton quaternary @click="batchDivisions('disable'); divDropdownOpen = false">批量停用</NButton>
                <NButton quaternary @click="batchDivisions('delete'); divDropdownOpen = false" class="dropdown-item-danger">批量删除</NButton>
              </div>
            </div>
            <NButton type="primary" @click="openDivForm()">+ 新建核算组织</NButton>
          </div>
        </div>
        <div v-if="!filteredDivisions.length" class="empty-state">
          <div class="empty-icon">&#x1F4CB;</div>
          <h4>暂无核算组织</h4>
          <p>点击右上角「+ 新建核算组织」添加</p>
        </div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="col-ck"><input type="checkbox" :checked="isAllDivisionsSelected" @change="toggleAllDivisions" /></th>
                <th style="width:50px">ID</th>
                <th style="width:90px">编码</th>
                <th style="min-width:140px">核算组织名称</th>
                <th style="width:70px">排序</th>
                <th style="width:70px">状态</th>
                <th style="width:150px">创建时间</th>
                <th style="width:180px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in filteredDivisions" :key="d.id"
                  :class="{ disabled: d.status === 'disabled', selected: selectedDivIds.includes(d.id) }" @dblclick="openDivForm(d)">
                <td class="col-ck"><input type="checkbox" :value="d.id" v-model="selectedDivIds" /></td>
                <td>{{ d.id }}</td>
                <td><strong>{{ d.division_code || '-' }}</strong></td>
                <td>{{ d.name }}</td>
                <td>{{ d.sort_order ?? '-' }}</td>
                <td><span class="tag" :class="d.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ d.status === 'enabled' ? '启用' : '停用' }}</span></td>
                <td>{{ d.created_at ? d.created_at.slice(0, 19).replace('T', ' ') : '-' }}</td>
                <td class="action-cell">
                  <NButton secondary size="small" @click="openDivForm(d)">编辑</NButton>
                  <NButton secondary size="small" v-if="d.status==='enabled'" @click="toggleDivStatus(d,'disabled')">停用</NButton>
                  <NButton secondary size="small" v-else @click="toggleDivStatus(d,'enabled')">启用</NButton>
                  <NButton type="warning" size="small" @click="deleteDiv(d)">删除</NButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ==================== 标签页3: 单位管理 ==================== -->
      <div v-show="activeTab === 'entities'">
        <div class="filters-bar">
          <NSelect v-model:value="entFilterDiv" :options="divisionFilterOptions" placeholder="全部核算组织" clearable />
          <input v-model="entKeyword" class="filter" placeholder="搜索单位编码/名称" style="width:200px" />
          <NSelect v-model:value="entFilterStatus" :options="STATUS_FILTER_OPTIONS_2" style="width:110px" />
          <div class="filter-spacer"></div>
          <div class="btn-row">
            <div class="dropdown" :class="{ open: entDropdownOpen }" v-if="selectedEntIds.length > 0">
              <NButton secondary @click="entDropdownOpen = !entDropdownOpen">批量操作 ({{ selectedEntIds.length }})</NButton>
              <div class="dropdown-menu">
                <NButton quaternary @click="batchEntities('enable'); entDropdownOpen = false">批量启用</NButton>
                <NButton quaternary @click="batchEntities('disable'); entDropdownOpen = false">批量停用</NButton>
                <NButton quaternary @click="batchEntities('delete'); entDropdownOpen = false" class="dropdown-item-danger">批量删除</NButton>
              </div>
            </div>
            <NButton type="primary" @click="openEntForm()">+ 新建单位</NButton>
          </div>
        </div>
        <div v-if="!filteredEntities_list.length" class="empty-state">
          <div class="empty-icon">&#x1F3E2;</div>
          <h4>暂无单位</h4>
          <p>点击右上角「+ 新建单位」添加，或通过账户列表批量导入</p>
        </div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th class="col-ck"><input type="checkbox" :checked="isAllEntitiesSelected" @change="toggleAllEntities" /></th>
                <th style="width:50px">ID</th>
                <th style="min-width:120px">所属核算组织</th>
                <th style="width:90px">单位编码</th>
                <th style="min-width:160px">单位全称</th>
                <th style="width:100px">单位简称</th>
                <th style="width:70px">状态</th>
                <th style="width:150px">创建时间</th>
                <th style="width:180px">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in filteredEntities_list" :key="e.id"
                  :class="{ disabled: e.status === 'disabled', selected: selectedEntIds.includes(e.id) }" @dblclick="openEntForm(e)">
                <td class="col-ck"><input type="checkbox" :value="e.id" v-model="selectedEntIds" /></td>
                <td>{{ e.id }}</td>
                <td>{{ e.division_name || '-' }}</td>
                <td><strong>{{ e.entity_code }}</strong></td>
                <td>{{ e.name || '-' }}</td>
                <td>{{ e.short_name || '-' }}</td>
                <td><span class="tag" :class="e.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ e.status === 'enabled' ? '启用' : '停用' }}</span></td>
                <td>{{ e.created_at ? e.created_at.slice(0, 19).replace('T', ' ') : '-' }}</td>
                <td class="action-cell">
                  <NButton secondary size="small" @click="openEntForm(e)">编辑</NButton>
                  <NButton secondary size="small" v-if="e.status==='enabled'" @click="toggleEntStatus(e,'disabled')">停用</NButton>
                  <NButton secondary size="small" v-else @click="toggleEntStatus(e,'enabled')">启用</NButton>
                  <NButton type="warning" size="small" @click="deleteEnt(e)">删除</NButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ==================== 标签页4: 银行账户管理 ==================== -->
      <div v-show="activeTab === 'banks'">
        <div class="filters-bar">
          <input v-model="bankKeyword" class="filter" placeholder="搜索账户编号/开户银行/银行账号" style="width:220px" />
          <NSelect v-model:value="bankFilterStatus" :options="STATUS_FILTER_OPTIONS_2" style="width:110px" />
          <div class="filter-spacer"></div>
          <div class="btn-row">
            <div class="dropdown" :class="{ open: bankDropdownOpen }" v-if="selectedBankIds.length > 0">
              <NButton secondary @click="bankDropdownOpen = !bankDropdownOpen">批量操作 ({{ selectedBankIds.length }})</NButton>
              <div class="dropdown-menu">
                <NButton quaternary @click="batchBanks('enable'); bankDropdownOpen = false">批量启用</NButton>
                <NButton quaternary @click="batchBanks('disable'); bankDropdownOpen = false">批量停用</NButton>
                <NButton quaternary @click="batchBanks('delete'); bankDropdownOpen = false" class="dropdown-item-danger">批量删除</NButton>
              </div>
            </div>
            <NButton type="primary" @click="openBankForm()">+ 新建银行账户</NButton>
          </div>
        </div>
        <!-- 无数据时 -->
        <div v-if="!filteredBankAccounts.length" style="text-align:center;color:var(--muted);padding:40px 0">
          暂无银行账户数据
        </div>
        <!-- 有数据时：动态列表格 -->
        <template v-else>
        <div class="table-wrap table-wrap-wide">
          <table>
            <thead>
              <tr>
                <th class="col-ck"><input type="checkbox" :checked="isAllBanksSelected" @change="toggleAllBanks" /></th>
                <th v-for="col in activeBankColumns" :key="col.key">{{ col.label }}</th>
                <th class="col-action">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in filteredBankAccounts" :key="a.id"
                  :class="{ disabled: a.status === 'disabled', selected: selectedBankIds.includes(a.id) }" @dblclick="openBankForm(a)">
                <td class="col-ck"><input type="checkbox" :value="a.id" v-model="selectedBankIds" /></td>
                <td v-for="col in activeBankColumns" :key="col.key" :class="col.type === 'money' ? 'money' : (col.type === 'code' || col.type === 'text' && (col.key === 'account_number' || col.key === 'account_last_four') ? 'mono' : '')">
                  <template v-if="col.type === 'bool'">
                    <span :class="getBoolVal(a, col.key) ? 'bool-yes' : 'bool-no'">{{ getBoolVal(a, col.key) ? '是' : '否' }}</span>
                  </template>
                  <span v-else-if="col.type === 'tag'" class="tag" :class="col.key === 'account_type' ? 'tag-blue' : 'tag-gray'">{{ a[col.key] || '-' }}</span>
                  <span v-else-if="col.type === 'status'" class="tag" :class="a.status === 'enabled' ? 'tag-green' : 'tag-warn'">{{ a.status === 'enabled' ? '启用' : '停用' }}</span>
                  <template v-else-if="col.type === 'money'">{{ fmtMoney(a[col.key]) }}</template>
                  <strong v-else-if="col.type === 'code'">{{ a[col.key] }}</strong>
                  <template v-else-if="col.type === 'input_method'">{{ a.input_method === 'bank_import' ? '银行导入' : (a.input_method === 'manual' ? '手工填写' : (a.input_method || '手工填写')) }}</template>
                  <template v-else>{{ a[col.key] || '-' }}</template>
                </td>
                <td class="action-cell">
                  <NButton secondary size="small" @click="openBankForm(a)">编辑</NButton>
                  <NButton secondary size="small" v-if="a.status==='enabled'" @click="toggleBankAccountStatus(a,'disabled')">停用</NButton>
                  <NButton secondary size="small" v-else @click="toggleBankAccountStatus(a,'enabled')">启用</NButton>
                  <NButton type="warning" size="small" @click="deleteBank(a)">删除</NButton>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="bottom-bar">
          <span class="count-info">共 {{ filteredBankAccounts.length }} 条银行账户记录</span>
        </div>
        </template>
      </div>
    </div>

    <!-- ==================== 弹窗：账户表单 ==================== -->
    <div class="modal-mask" v-if="showAccountForm" @click.self="showAccountForm=false">
      <div class="modal modal-lg">
        <h3>{{ editingAccount ? '编辑账户' : '新建账户' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">所属单位 *</label>
            <NSelect v-model:value="accountForm.entity_id" :options="entityGroupOptions" placeholder="-- 请选择所属单位 --" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">账户编号 *</label>
            <input v-model="accountForm.account_code" class="form-input" placeholder="留空自动生成（ZH0001）" :disabled="!!editingAccount" />
          </div>
          <div class="form-group">
            <label class="form-label">开户银行</label>
            <input v-model="accountForm.bank_name" class="form-input" placeholder="如 中国银行" />
          </div>
          <div class="form-group">
            <label class="form-label">银行账号</label>
            <input v-model="accountForm.account_number" class="form-input" placeholder="完整账号，不加空格" />
          </div>
          <div class="form-group">
            <label class="form-label">账户名称</label>
            <input v-model="accountForm.branch_name" class="form-input" placeholder="如 中国银行上海浦东支行" />
          </div>
          <div class="form-group">
            <label class="form-label">账户后四位</label>
            <input v-model="accountForm.account_last_four" class="form-input" placeholder="银行账号后四位" />
          </div>
          <div class="form-group">
            <label class="form-label">账户类型 *</label>
            <NSelect v-model:value="accountForm.account_type" :options="ACCOUNT_TYPE_OPTIONS" placeholder="-- 请选择 --" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">资金类型 *</label>
            <NSelect v-model:value="accountForm.instrument_type" :options="INSTRUMENT_TYPE_OPTIONS" placeholder="-- 请选择 --" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">是否网银 *</label>
            <NSelect v-model:value="accountForm.has_online_banking" :options="BOOL_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">录入方式 *</label>
            <NSelect v-model:value="accountForm.input_method" :options="INPUT_METHOD_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">币种</label>
            <input v-model="accountForm.currency" class="form-input" placeholder="CNY" />
          </div>
          <div class="form-group" v-if="!editingAccount">
            <label class="form-label">期初余额 *</label>
            <input v-model.number="accountForm.initial_balance" type="number" step="0.01" class="form-input" placeholder="系统起算余额" />
          </div>
          <div class="form-group" v-if="!editingAccount">
            <label class="form-label">余额日期 *</label>
            <NDatePicker v-model:value="accountForm.balance_date" type="date" value-format="yyyy-MM-dd" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">是否纳入日报</label>
            <NSelect v-model:value="accountForm.include_in_daily_report" :options="BOOL_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">是否允许手工录入</label>
            <NSelect v-model:value="accountForm.allow_manual_entry" :options="BOOL_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group" v-if="editingAccount">
            <label class="form-label">状态</label>
            <NSelect v-model:value="accountForm.status" :options="STATUS_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label class="form-label">备注</label>
            <input v-model="accountForm.notes" class="form-input" placeholder="补充说明" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <NButton secondary @click="showAccountForm=false">取消</NButton>
          <NButton type="primary" @click="saveAccount">保存</NButton>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：核算组织表单 ==================== -->
    <div class="modal-mask" v-if="showDivForm" @click.self="showDivForm=false">
      <div class="modal">
        <h3>{{ editingDiv ? '编辑核算组织' : '新建核算组织' }}</h3>
        <div class="form-grid">
          <div class="form-group" v-if="editingDiv">
            <label class="form-label">编码</label>
            <input :value="editingDiv.division_code" class="form-input" disabled />
          </div>
          <div class="form-group">
            <label class="form-label">名称 *</label>
            <input v-model="divForm.name" class="form-input" placeholder="核算组织名称" />
          </div>
          <div class="form-group">
            <label class="form-label">排序</label>
            <input v-model.number="divForm.sort_order" type="number" class="form-input" placeholder="数值越小越靠前" />
          </div>
          <div class="form-group" v-if="editingDiv">
            <label class="form-label">状态</label>
            <NSelect v-model:value="divForm.status" :options="STATUS_OPTIONS" style="width:100%" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <NButton secondary @click="showDivForm=false">取消</NButton>
          <NButton type="primary" @click="saveDiv">保存</NButton>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：单位表单 ==================== -->
    <div class="modal-mask" v-if="showEntForm" @click.self="showEntForm=false">
      <div class="modal modal-lg">
        <h3>{{ editingEnt ? '编辑单位' : '新建单位' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">所属核算组织 *</label>
            <NSelect v-model:value="entForm.division_id" :options="divisionFilterOptions" placeholder="-- 请选择核算组织 --" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">单位编码</label>
            <input v-if="editingEnt" :value="editingEnt.entity_code" class="form-input" disabled />
            <input v-else v-model="entForm.entity_code" class="form-input" placeholder="留空自动生成" />
          </div>
          <div class="form-group">
            <label class="form-label">单位全称 *</label>
            <input v-model="entForm.name" class="form-input" placeholder="单位全称" />
          </div>
          <div class="form-group">
            <label class="form-label">单位简称 *</label>
            <input v-model="entForm.short_name" class="form-input" placeholder="单位简称" />
          </div>
          <div class="form-group" v-if="editingEnt">
            <label class="form-label">状态</label>
            <NSelect v-model:value="entForm.status" :options="STATUS_OPTIONS" style="width:100%" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <NButton secondary @click="showEntForm=false">取消</NButton>
          <NButton type="primary" @click="saveEnt">保存</NButton>
        </div>
      </div>
    </div>

    <!-- ==================== 弹窗：银行账户表单 ==================== -->
    <div class="modal-mask" v-if="showBankForm" @click.self="showBankForm=false">
      <div class="modal modal-lg">
        <h3>{{ editingBank ? '编辑银行账户' : '新建银行账户' }}</h3>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">所属单位 *</label>
            <NSelect v-model:value="bankForm.entity_id" :options="entityGroupOptions" placeholder="-- 请选择所属单位 --" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">开户银行</label>
            <input v-model="bankForm.bank_name" class="form-input" placeholder="如 中国银行" />
          </div>
          <div class="form-group">
            <label class="form-label">银行账号</label>
            <input v-model="bankForm.account_number" class="form-input" placeholder="完整账号，不加空格" />
          </div>
          <div class="form-group">
            <label class="form-label">开户行名称</label>
            <input v-model="bankForm.branch_name" class="form-input" placeholder="如 中国银行上海浦东支行" />
          </div>
          <div class="form-group">
            <label class="form-label">账户后四位</label>
            <input v-model="bankForm.account_last_four" class="form-input" placeholder="留空自动从银行账号提取" />
          </div>
          <div class="form-group">
            <label class="form-label">账户类型</label>
            <NSelect v-model:value="bankForm.account_type" :options="BANK_ACCOUNT_TYPE_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">资金类型</label>
            <NSelect v-model:value="bankForm.instrument_type" :options="BANK_INSTRUMENT_TYPE_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">是否网银</label>
            <NSelect v-model:value="bankForm.has_online_banking" :options="BOOL_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">录入方式</label>
            <NSelect v-model:value="bankForm.input_method" :options="INPUT_METHOD_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">币种</label>
            <input v-model="bankForm.currency" class="form-input" placeholder="CNY" />
          </div>
          <div class="form-group" v-if="!editingBank">
            <label class="form-label">期初余额</label>
            <input v-model.number="bankForm.initial_balance" type="number" step="0.01" class="form-input" placeholder="系统起算余额" />
          </div>
          <div class="form-group" v-if="!editingBank">
            <label class="form-label">余额日期</label>
            <NDatePicker v-model:value="bankForm.balance_date" type="date" value-format="yyyy-MM-dd" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">是否纳入日报</label>
            <NSelect v-model:value="bankForm.include_in_daily_report" :options="BOOL_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group">
            <label class="form-label">是否允许手工录入</label>
            <NSelect v-model:value="bankForm.allow_manual_entry" :options="BOOL_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group" v-if="editingBank">
            <label class="form-label">状态</label>
            <NSelect v-model:value="bankForm.status" :options="STATUS_OPTIONS" style="width:100%" />
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label class="form-label">备注</label>
            <input v-model="bankForm.notes" class="form-input" placeholder="补充说明" />
          </div>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <NButton secondary @click="showBankForm=false">取消</NButton>
          <NButton type="primary" @click="saveBank">保存</NButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NDatePicker, NSelect, NButton } from 'naive-ui'
import * as api from '@/api/master'
import { fmtAmt } from '@/utils/format'

// ── NSelect 选项常量 ──
const STATUS_FILTER_OPTIONS = [
  { label: '全部', value: '' },
  { label: '启用', value: 'enabled' },
  { label: '停用', value: 'disabled' },
]
const STATUS_FILTER_OPTIONS_2 = [
  { label: '全部状态', value: '' },
  { label: '启用', value: 'enabled' },
  { label: '停用', value: 'disabled' },
]
const STATUS_OPTIONS = [
  { label: '启用', value: 'enabled' },
  { label: '停用', value: 'disabled' },
]
const ACCOUNT_TYPE_OPTIONS = [
  { label: '基本户', value: '基本户' }, { label: '一般户', value: '一般户' },
  { label: '临时户', value: '临时户' }, { label: '现金账户', value: '现金账户' },
  { label: '农民工工资专用账户', value: '农民工工资专用账户' },
  { label: '票据账户', value: '票据账户' }, { label: '信用证账户', value: '信用证账户' },
  { label: '贷款账户', value: '贷款账户' }, { label: '其他账户', value: '其他账户' },
]
const INSTRUMENT_TYPE_OPTIONS = [
  { label: '银行存款', value: '银行存款' }, { label: '现金', value: '现金' },
  { label: '票据', value: '票据' }, { label: '信用证', value: '信用证' },
  { label: '保证金', value: '保证金' }, { label: '其他', value: '其他' },
]
const BOOL_OPTIONS = [{ label: '是', value: true }, { label: '否', value: false }]
const INPUT_METHOD_OPTIONS = [{ label: '网银导入', value: '网银导入' }, { label: '手工填写', value: '手工填写' }]
const BANK_ACCOUNT_TYPE_OPTIONS = [
  { label: '银行账户', value: '银行账户' }, { label: '现金', value: '现金' },
  { label: '票据', value: '票据' }, { label: '其他', value: '其他' },
]
const BANK_INSTRUMENT_TYPE_OPTIONS = [
  { label: '银行存款', value: '银行存款' }, { label: '现金', value: '现金' },
  { label: '票据', value: '票据' }, { label: '受限资金', value: '受限资金' },
]

// ── 公共数据 ──
const divisions = ref([])
const allEntities = ref([])
const accounts = ref([])
const banks = ref([])
const importInput = ref(null)
const activeTab = ref('accounts')

// ── 默认列定义（无导入模板时的兜底） ──
const DEFAULT_ACCOUNT_COLUMNS = [
  { key: 'division_name', label: '核算组织', type: 'text' },
  { key: 'entity_name', label: '所属单位', type: 'text' },
  { key: 'account_code', label: '账户编号', type: 'code' },
  { key: 'bank_name', label: '开户银行', type: 'text' },
  { key: 'account_number', label: '银行账号', type: 'text' },
  { key: 'branch_name', label: '开户行名称', type: 'text' },
  { key: 'account_type', label: '账户类型', type: 'tag' },
  { key: 'instrument_type', label: '资金类型', type: 'tag' },
  { key: 'initial_balance', label: '期初余额', type: 'money' },
  { key: 'status', label: '状态', type: 'status' },
]

const DEFAULT_BANK_COLUMNS = [
  { key: 'entity_name', label: '所属单位', type: 'text' },
  { key: 'account_code', label: '账户编号', type: 'code' },
  { key: 'bank_name', label: '开户银行', type: 'text' },
  { key: 'account_number', label: '银行账号', type: 'text' },
  { key: 'branch_name', label: '开户行名称', type: 'text' },
  { key: 'account_type', label: '账户类型', type: 'tag' },
  { key: 'instrument_type', label: '资金类型', type: 'tag' },
  { key: 'has_online_banking', label: '网银', type: 'bool' },
  { key: 'initial_balance', label: '期初余额', type: 'money' },
  { key: 'status', label: '状态', type: 'status' },
]

// ── 动态列定义：从后端获取（基于用户导入的模板列名） ──
const accountColumns = ref([])

// 银行账户标签页用的列（从账户列中筛选银行相关字段）
const bankAccountColumns = computed(() => {
  const bankKeys = ['bank_name', 'account_number', 'branch_name', 'account_code',
    'account_last_four', 'account_type', 'instrument_type', 'has_online_banking',
    'input_method', 'currency', 'initial_balance', 'balance_date',
    'include_in_daily_report', 'allow_manual_entry', 'status']
  return accountColumns.value.filter(c => bankKeys.includes(c.key))
})

// ── 批量选择 ──
const selectedAccountIds = ref([])
const selectedDivIds = ref([])
const selectedEntIds = ref([])
const selectedBankIds = ref([])

// ── 下拉菜单开关 ──
const accDropdownOpen = ref(false)
const divDropdownOpen = ref(false)
const entDropdownOpen = ref(false)
const bankDropdownOpen = ref(false)

// ── 账户筛选 ──
const filterDivision = ref(null)
const filterEntity = ref(null)
const filterStatus = ref('')
const keyword = ref('')

// ── 核算组织筛选 ──
const divFilterStatus = ref('')

// ── 单位筛选 ──
const entFilterDiv = ref(null)
const entFilterStatus = ref('')
const entKeyword = ref('')

// ── 银行筛选 ──
const bankKeyword = ref('')
const bankFilterStatus = ref('')

// ── 账户表单 ──
const showAccountForm = ref(false)
const editingAccount = ref(null)
const accountForm = ref(makeAccountForm())

function makeAccountForm() {
  return {
    entity_id: null, account_code: '', bank_name: '', branch_name: '',
    account_number: '', account_last_four: '', account_type: '', instrument_type: '',
    has_online_banking: false, input_method: '手工填写', currency: 'CNY',
    include_in_daily_report: true, allow_manual_entry: true,
    initial_balance: 0, balance_date: '',
    status: 'enabled', notes: '',
  }
}

// ── 核算组织表单 ──
const showDivForm = ref(false)
const editingDiv = ref(null)
const divForm = ref({ name: '', sort_order: 0, status: 'enabled' })

// ── 单位表单 ──
const showEntForm = ref(false)
const editingEnt = ref(null)
const entForm = ref({ division_id: null, entity_code: '', name: '', short_name: '', status: 'enabled' })

// ── 银行账户表单 ──
const showBankForm = ref(false)
const editingBank = ref(null)
const bankForm = ref({
  entity_id: null, account_code: '', bank_name: '', branch_name: '',
  account_number: '', account_last_four: '', account_type: '银行账户',
  instrument_type: '银行存款', has_online_banking: false, input_method: '手工填写',
  currency: 'CNY', include_in_daily_report: true, allow_manual_entry: true,
  initial_balance: 0, balance_date: '', status: 'enabled', notes: ''
})

// ── 计算属性 ──
const filteredEntities = computed(() => {
  if (!filterDivision.value) return allEntities.value
  return allEntities.value.filter(e => e.division_id === filterDivision.value)
})

const getEntitiesForDivision = (divisionId) => {
  return allEntities.value.filter(e => e.division_id === divisionId)
}

const ungroupedEntities = computed(() => {
  return allEntities.value.filter(e => !e.division_id)
})

const divisionFilterOptions = computed(() => [
  { label: '全部核算组织', value: null },
  ...divisions.value.map(d => ({ label: d.name, value: d.id }))
])
const entityFilterSelectOptions = computed(() => [
  { label: '全部单位', value: null },
  ...filteredEntities.value.map(e => ({ label: e.short_name, value: e.id }))
])
const entityGroupOptions = computed(() => {
  const opts = []
  for (const d of divisions.value) {
    const children = getEntitiesForDivision(d.id).map(e => ({
      label: `${e.short_name}（${e.entity_code}）`, value: e.id
    }))
    if (children.length) opts.push({ type: 'group', label: d.name, key: `div-${d.id}`, children })
  }
  return [...opts, ...ungroupedEntities.value.map(e => ({ label: `${e.short_name}（${e.entity_code}）`, value: e.id }))]
})

const filteredAccounts = computed(() => {
  let list = accounts.value
  if (filterEntity.value) list = list.filter(a => a.entity_id === filterEntity.value)
  if (filterStatus.value) list = list.filter(a => a.status === filterStatus.value)
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(a =>
      (a.account_code || '').toLowerCase().includes(kw) ||
      (a.account_alias || '').toLowerCase().includes(kw) ||
      (a.bank_name || '').toLowerCase().includes(kw) ||
      (a.account_number || '').toLowerCase().includes(kw) ||
      (a.entity_name || '').toLowerCase().includes(kw)
    )
  }
  return list
})

const filteredDivisions = computed(() => {
  let items = divisions.value
  if (divFilterStatus.value) items = items.filter(d => d.status === divFilterStatus.value)
  return items
})

const filteredEntities_list = computed(() => {
  let items = allEntities.value
  if (entFilterDiv.value) items = items.filter(e => e.division_id === entFilterDiv.value)
  if (entFilterStatus.value) items = items.filter(e => e.status === entFilterStatus.value)
  if (entKeyword.value) {
    const kw = entKeyword.value.toLowerCase()
    items = items.filter(e =>
      (e.entity_code || '').toLowerCase().includes(kw) ||
      (e.name || '').toLowerCase().includes(kw) ||
      (e.short_name || '').toLowerCase().includes(kw)
    )
  }
  return items
})

const BANK_ACCOUNT_TYPES = ['银行账户', '基本户', '一般户', '临时户', '农民工工资专用账户', '信用证账户', '贷款账户']

const filteredBankAccounts = computed(() => {
  let items = accounts.value.filter(a =>
    a.bank_name ||
    BANK_ACCOUNT_TYPES.includes(a.account_type) ||
    a.instrument_type === '银行存款'
  )
  if (bankFilterStatus.value) items = items.filter(a => a.status === bankFilterStatus.value)
  if (bankKeyword.value) {
    const kw = bankKeyword.value.toLowerCase()
    items = items.filter(a =>
      (a.account_code || '').toLowerCase().includes(kw) ||
      (a.bank_name || '').toLowerCase().includes(kw) ||
      (a.account_number || '').toLowerCase().includes(kw)
    )
  }
  return items
})

// 动态列：无模板时用默认列，有模板时过滤掉全空列
const activeAccountColumns = computed(() => {
  const accs = accounts.value
  if (!accs.length) return []
  const cols = accountColumns.value.length > 0 ? accountColumns.value : DEFAULT_ACCOUNT_COLUMNS
  return cols.filter(col => {
    return accs.some(a => {
      const v = a[col.key]
      if (v === null || v === undefined) return false
      if (typeof v === 'string' && v.trim() === '') return false
      return true
    })
  })
})

const activeBankColumns = computed(() => {
  const accs = filteredBankAccounts.value
  if (!accs.length) return []
  const raw = bankAccountColumns.value
  const cols = raw.length > 0 ? raw : DEFAULT_BANK_COLUMNS
  return cols.filter(col => {
    return accs.some(a => {
      const v = a[col.key]
      if (v === null || v === undefined) return false
      if (typeof v === 'string' && v.trim() === '') return false
      return true
    })
  })
})

function getBoolVal(account, key) {
  return account[key] !== false
}

// ── 全选计算属性 ──
const isAllAccountsSelected = computed(() => {
  const list = filteredAccounts.value
  return list.length > 0 && list.every(a => selectedAccountIds.value.includes(a.id))
})

const isAllDivisionsSelected = computed(() => {
  const list = filteredDivisions.value
  return list.length > 0 && list.every(d => selectedDivIds.value.includes(d.id))
})

const isAllEntitiesSelected = computed(() => {
  const list = filteredEntities_list.value
  return list.length > 0 && list.every(e => selectedEntIds.value.includes(e.id))
})

const isAllBanksSelected = computed(() => {
  const list = filteredBankAccounts.value
  return list.length > 0 && list.every(a => selectedBankIds.value.includes(a.id))
})

function toggleAllAccounts() {
  if (isAllAccountsSelected.value) {
    selectedAccountIds.value = []
  } else {
    selectedAccountIds.value = filteredAccounts.value.map(a => a.id)
  }
}

function toggleAllDivisions() {
  if (isAllDivisionsSelected.value) {
    selectedDivIds.value = []
  } else {
    selectedDivIds.value = filteredDivisions.value.map(d => d.id)
  }
}

function toggleAllEntities() {
  if (isAllEntitiesSelected.value) {
    selectedEntIds.value = []
  } else {
    selectedEntIds.value = filteredEntities_list.value.map(e => e.id)
  }
}

function toggleAllBanks() {
  if (isAllBanksSelected.value) {
    selectedBankIds.value = []
  } else {
    selectedBankIds.value = filteredBankAccounts.value.map(a => a.id)
  }
}

// ── 批量操作 ──
async function batchAccounts(action) {
  const ids = [...selectedAccountIds.value]
  if (!ids.length) return
  const labels = { enable: '启用', disable: '停用', delete: '删除' }
  const label = labels[action] || action
  if (!confirm(`确定批量${label} ${ids.length} 个账户？${action === 'delete' ? '此操作不可撤销！' : ''}`)) return
  try {
    const result = await api.batchActionAccounts(ids, action)
    const failedCount = result.failed?.length || 0
    if (failedCount > 0) {
      const msgs = result.failed.map(f => f.message).join('\n')
      alert(`${result.success} 条成功，${failedCount} 条失败：\n${msgs}`)
    }
    selectedAccountIds.value = []
    if (action === 'delete') {
      await loadAll()
    } else {
      await loadAccounts()
    }
  } catch (e) { alert(e.message || '批量操作失败') }
}

async function batchDivisions(action) {
  const ids = [...selectedDivIds.value]
  if (!ids.length) return
  const labels = { enable: '启用', disable: '停用', delete: '删除' }
  const label = labels[action] || action
  if (!confirm(`确定批量${label} ${ids.length} 个核算组织？${action === 'delete' ? '此操作不可撤销！' : ''}`)) return
  try {
    const result = await api.batchActionDivisions(ids, action)
    const failedCount = result.failed?.length || 0
    if (failedCount > 0) {
      const msgs = result.failed.map(f => f.message).join('\n')
      alert(`${result.success} 条成功，${failedCount} 条失败：\n${msgs}`)
    }
    selectedDivIds.value = []
    await loadAll()
  } catch (e) { alert(e.message || '批量操作失败') }
}

async function batchEntities(action) {
  const ids = [...selectedEntIds.value]
  if (!ids.length) return
  const labels = { enable: '启用', disable: '停用', delete: '删除' }
  const label = labels[action] || action
  if (!confirm(`确定批量${label} ${ids.length} 个单位？${action === 'delete' ? '此操作不可撤销！' : ''}`)) return
  try {
    const result = await api.batchActionEntities(ids, action)
    const failedCount = result.failed?.length || 0
    if (failedCount > 0) {
      const msgs = result.failed.map(f => f.message).join('\n')
      alert(`${result.success} 条成功，${failedCount} 条失败：\n${msgs}`)
    }
    selectedEntIds.value = []
    await loadAll()
  } catch (e) { alert(e.message || '批量操作失败') }
}

async function batchBanks(action) {
  const ids = [...selectedBankIds.value]
  if (!ids.length) return
  const labels = { enable: '启用', disable: '停用', delete: '删除' }
  const label = labels[action] || action
  if (!confirm(`确定批量${label} ${ids.length} 个银行账户？${action === 'delete' ? '此操作不可撤销！' : ''}`)) return
  try {
    const result = await api.batchActionAccounts(ids, action)
    const failedCount = result.failed?.length || 0
    if (failedCount > 0) {
      const msgs = result.failed.map(f => f.message).join('\n')
      alert(`${result.success} 条成功，${failedCount} 条失败：\n${msgs}`)
    }
    selectedBankIds.value = []
    if (action === 'delete') {
      await loadAll()
    } else {
      await loadAccounts()
    }
  } catch (e) { alert(e.message || '批量操作失败') }
}

// ── 数据加载 ──
async function loadAccounts() {
  try {
    const res = await api.getAccounts({ page: 1, page_size: 200 })
    accounts.value = res?.items || []
    if (res?.columns) accountColumns.value = res.columns
  } catch (e) { console.error(e) }
}

async function loadAll() {
  try {
    const [divs, ents, accs, bnks] = await Promise.all([
      api.getDivisions(),
      api.getEntities({ page: 1, page_size: 200 }),
      api.getAccounts({ page: 1, page_size: 200 }),
      api.getBanks({ page: 1, page_size: 200 }),
    ])
    divisions.value = divs || []
    allEntities.value = ents?.items || []
    accounts.value = accs?.items || []
    if (accs?.columns) accountColumns.value = accs.columns
    banks.value = Array.isArray(bnks) ? bnks : (bnks?.items || [])
  } catch (e) { console.error(e) }
}

// ── 账户操作 ──
function openAccountForm(acc) {
  if (acc) {
    editingAccount.value = acc
    accountForm.value = {
      entity_id: acc.entity_id, account_code: acc.account_code,
      bank_name: acc.bank_name || '', branch_name: acc.branch_name || '',
      account_number: acc.account_number || '', account_last_four: acc.account_last_four || '',
      account_type: acc.account_type || '', instrument_type: acc.instrument_type || '',
      has_online_banking: acc.has_online_banking || false,
      input_method: acc.input_method === 'bank_import' ? '网银导入' : '手工填写',
      currency: acc.currency, include_in_daily_report: acc.include_in_daily_report !== false,
      allow_manual_entry: acc.allow_manual_entry !== false,
      initial_balance: acc.initial_balance, balance_date: acc.balance_date,
      status: acc.status, notes: acc.notes || '',
    }
  } else {
    editingAccount.value = null
    accountForm.value = {
      ...makeAccountForm(),
      balance_date: new Date().toISOString().slice(0, 10),
    }
  }
  showAccountForm.value = true
}

async function saveAccount() {
  try {
    const code = accountForm.value.account_code?.trim() || ''
    const payload = {
      entity_id: accountForm.value.entity_id,
      account_code: code || undefined,
      account_alias: accountForm.value.account_type || code || undefined,
      bank_name: accountForm.value.bank_name, branch_name: accountForm.value.branch_name,
      account_number: accountForm.value.account_number,
      account_last_four: accountForm.value.account_last_four || (accountForm.value.account_number ? accountForm.value.account_number.slice(-4) : ''),
      account_type: accountForm.value.account_type, instrument_type: accountForm.value.instrument_type,
      has_online_banking: accountForm.value.has_online_banking,
      input_method: accountForm.value.input_method === '网银导入' ? 'bank_import' : 'manual',
      include_in_daily_report: accountForm.value.include_in_daily_report,
      allow_manual_entry: accountForm.value.allow_manual_entry,
      currency: accountForm.value.currency, notes: accountForm.value.notes,
    }
    if (editingAccount.value) {
      payload.status = accountForm.value.status
      await api.updateAccount(editingAccount.value.id, payload)
    } else {
      payload.initial_balance = accountForm.value.initial_balance
      payload.balance_date = accountForm.value.balance_date
      await api.createAccount(payload)
    }
    showAccountForm.value = false
    await loadAccounts()
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleAccountStatus(acc, status) {
  try {
    await api.updateAccount(acc.id, { status })
    await loadAccounts()
  } catch (e) { alert(e.message) }
}

// ── 核算组织操作 ──
function openDivForm(item) {
  if (item) {
    editingDiv.value = item
    divForm.value = { name: item.name || '', sort_order: item.sort_order ?? 0, status: item.status || 'enabled' }
  } else {
    editingDiv.value = null
    divForm.value = { name: '', sort_order: 0, status: 'enabled' }
  }
  showDivForm.value = true
}

async function saveDiv() {
  if (!divForm.value.name.trim()) { alert('请填写核算组织名称'); return }
  try {
    const payload = { name: divForm.value.name.trim(), sort_order: divForm.value.sort_order || 0 }
    if (editingDiv.value) {
      payload.status = divForm.value.status
      await api.updateDivision(editingDiv.value.id, payload)
    } else {
      await api.createDivision(payload)
    }
    showDivForm.value = false
    await loadAll()
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleDivStatus(item, status) {
  try {
    await api.updateDivisionStatus(item.id, status)
    await loadAll()
  } catch (e) { alert(e.message) }
}

async function deleteDiv(item) {
  try {
    const usage = await api.getDivisionUsage(item.id)
    const unitCount = usage.unit_count || 0
    if (unitCount > 0) {
      const unitNames = (usage.units || []).map(u => `${u.entity_code} ${u.name || u.short_name}`).join('、')
      alert(`该核算组织下有 ${unitCount} 个单位（${unitNames}），请先删除所有单位后再删除核算组织。`)
      return
    }
    if (!confirm(`确定删除核算组织「${item.name}」？此操作不可撤销。`)) return
    await api.deleteDivision(item.id)
    await loadAll()
  } catch (e) { alert(e.message || '删除失败') }
}

// ── 单位操作 ──
function openEntForm(item) {
  if (item) {
    editingEnt.value = item
    entForm.value = {
      division_id: item.division_id || null,
      entity_code: item.entity_code || '',
      name: item.name || item.full_name || '',
      short_name: item.short_name || '',
      status: item.status || 'enabled',
    }
  } else {
    editingEnt.value = null
    entForm.value = { division_id: null, entity_code: '', name: '', short_name: '', status: 'enabled' }
  }
  showEntForm.value = true
}

async function saveEnt() {
  if (!entForm.value.name.trim()) { alert('请填写单位全称'); return }
  if (!entForm.value.short_name.trim()) { alert('请填写单位简称'); return }
  try {
    const payload = {
      division_id: entForm.value.division_id,
      entity_code: entForm.value.entity_code.trim() || null,
      name: entForm.value.name.trim(),
      short_name: entForm.value.short_name.trim(),
    }
    if (editingEnt.value) {
      payload.status = entForm.value.status
      await api.updateEntity(editingEnt.value.id, payload)
    } else {
      await api.createEntity(payload)
    }
    showEntForm.value = false
    await loadAll()
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleEntStatus(item, status) {
  try {
    await api.updateEntityStatus(item.id, status)
    await loadAll()
  } catch (e) { alert(e.message) }
}

async function deleteEnt(item) {
  try {
    const usage = await api.getEntityUsage(item.id)
    const accountCount = usage.account_count || 0
    if (accountCount > 0) {
      const accNames = (usage.accounts || []).map(a => `${a.account_code} ${a.account_alias}（${a.account_type}）`).join('、')
      alert(`单位「${item.short_name || item.name}」下有 ${accountCount} 个银行账户（${accNames}），请先到「账户管理」中删除所有账户后再删除单位。`)
      return
    }
    if (!confirm(`确定删除单位「${item.short_name || item.name}」？此操作不可撤销。`)) return
    await api.deleteEntity(item.id)
    await loadAll()
  } catch (e) { alert(e.message || '删除失败') }
}

// ── 银行操作 ──
function openBankForm(item) {
  if (item) {
    editingBank.value = item
    bankForm.value = {
      entity_id: item.entity_id || null,
      account_code: item.account_code || '',
      bank_name: item.bank_name || '',
      branch_name: item.branch_name || '',
      account_number: item.account_number || '',
      account_last_four: item.account_last_four || '',
      account_type: item.account_type || '银行账户',
      instrument_type: item.instrument_type || '银行存款',
      has_online_banking: item.has_online_banking || false,
      input_method: item.input_method === 'bank_import' ? '网银导入' : '手工填写',
      currency: item.currency || 'CNY',
      include_in_daily_report: item.include_in_daily_report !== false,
      allow_manual_entry: item.allow_manual_entry !== false,
      initial_balance: item.initial_balance || 0,
      balance_date: item.balance_date || '',
      status: item.status || 'enabled',
      notes: item.notes || '',
    }
  } else {
    editingBank.value = null
    bankForm.value = {
      entity_id: null, account_code: '', bank_name: '', branch_name: '',
      account_number: '', account_last_four: '', account_type: '银行账户',
      instrument_type: '银行存款', has_online_banking: false, input_method: '手工填写',
      currency: 'CNY', include_in_daily_report: true, allow_manual_entry: true,
      initial_balance: 0, balance_date: new Date().toISOString().slice(0, 10),
      status: 'enabled', notes: '',
    }
  }
  showBankForm.value = true
}

async function saveBank() {
  if (!bankForm.value.bank_name.trim() && !bankForm.value.account_number.trim()) {
    alert('请至少填写开户银行或银行账号')
    return
  }
  try {
    const payload = {
      entity_id: bankForm.value.entity_id,
      account_code: bankForm.value.account_code?.trim() || undefined,
      bank_name: bankForm.value.bank_name.trim(),
      branch_name: bankForm.value.branch_name.trim(),
      account_number: bankForm.value.account_number.trim(),
      account_last_four: bankForm.value.account_last_four || (bankForm.value.account_number ? bankForm.value.account_number.slice(-4) : ''),
      account_type: bankForm.value.account_type,
      instrument_type: bankForm.value.instrument_type,
      has_online_banking: bankForm.value.has_online_banking,
      input_method: bankForm.value.input_method === '网银导入' ? 'bank_import' : 'manual',
      currency: bankForm.value.currency,
      include_in_daily_report: bankForm.value.include_in_daily_report,
      allow_manual_entry: bankForm.value.allow_manual_entry,
      notes: bankForm.value.notes.trim(),
    }
    if (editingBank.value) {
      payload.status = bankForm.value.status
      await api.updateAccount(editingBank.value.id, payload)
    } else {
      payload.initial_balance = bankForm.value.initial_balance
      payload.balance_date = bankForm.value.balance_date
      await api.createAccount(payload)
    }
    showBankForm.value = false
    await loadAccounts()
  } catch (e) { alert(e.message || '保存失败') }
}

async function toggleBankAccountStatus(item, status) {
  try {
    await api.updateAccount(item.id, { status })
    await loadAccounts()
  } catch (e) { alert(e.message) }
}

async function deleteBank(item) {
  if (!confirm(`确定删除银行账户「${item.account_code} ${item.bank_name || ''}」？此操作不可撤销。`)) return
  try {
    await api.batchActionAccounts([item.id], 'delete')
    await loadAll()
  } catch (e) { alert(e.message || '删除失败') }
}

// ── 工具 ──
function fmtMoney(v) { return fmtAmt(v) }

function downloadTemplate() { window.open('/api/accounts/template', '_blank') }

function triggerImport() { importInput.value.click() }

async function doImport(e) {
  const file = e.target.files[0]
  if (!file) return
  try {
    const d = await api.importAccounts(file)
    let msg = `导入完成！\n创建核算组织: ${d.created_divisions}\n创建单位: ${d.created_entities}\n创建账户: ${d.created_accounts}`
    if (d.error_count > 0) msg += `\n\n${d.error_count} 条错误：\n${d.errors.join('\n')}`
    alert(msg)
    await loadAll()
  } catch (e) { alert('导入出错: ' + e.message) }
  e.target.value = ''
}

onMounted(loadAll)
</script>

<style scoped>
@import './common.css';

/* 标签页栏 */
.tabs-bar {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--line);
  margin-bottom: var(--space-lg);
}
.tab-btn {
  padding: var(--space-sm) var(--space-xl);
  font-size: var(--font-size-base);
  font-family: inherit;
  font-weight: 500;
  color: var(--muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all .18s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active {
  color: var(--green);
  border-bottom-color: var(--green);
  font-weight: 600;
}

/* 表格滚动区 */
.table-wrap {
  flex: 1;
  overflow: auto;
  max-height: calc(100vh - 300px);
}
.table-wrap-wide {
  overflow-x: auto;
}

/* 禁用行 */
tr.disabled { opacity: 0.55; }
tr.selected { background: #f0f5ef; }

/* 空数据状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}
.empty-state .empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-state h4 {
  margin: 0 0 8px 0;
  color: var(--text);
  font-size: 16px;
}
.empty-state p {
  margin: 0;
  font-size: 13px;
}

/* 勾选列 */
.col-ck { width: 36px; text-align: center; }
.col-ck input[type="checkbox"] { cursor: pointer; }

/* 账户列表列宽 — 紧凑 */
.col-xs { width: 60px; }
.col-sm { width: 80px; }
.col-md { width: 120px; }
.col-num { width: 130px; }
.col-money { width: 90px; text-align: right; }
.col-date { width: 90px; }
.col-notes { min-width: 100px; }
.col-action { width: 120px; }

/* 布尔值 是/否 样式 */
.bool-yes {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  background: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}
.bool-no {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  background: #f5f5f5;
  color: #9e9e9e;
  border: 1px solid #e0e0e0;
}

/* 等宽字体 */
.mono { font-family: monospace; font-size: 12px; }

/* 长文本省略 */
.ellipsis { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }

/* 操作列不换行 */
.action-cell { white-space: nowrap; }

/* 下拉菜单 */
.dropdown { position: relative; display: inline-block; }
.dropdown-menu {
  display: none; position: absolute; right: 0; top: 100%;
  background: white; border: 1px solid #ddd; border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 100; min-width: 120px;
}
.dropdown-menu button {
  display: block; width: 100%; padding: 8px 16px; border: none;
  background: none; text-align: left; cursor: pointer; font-size: 13px;
}
.dropdown-menu button:hover { background: #f5f5f5; }
.dropdown.open .dropdown-menu { display: block; }
.dropdown-item-danger { color: #9b3d2f; }
.dropdown-item-danger:hover { background: #fdf2ef !important; }

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  overflow-y: auto;
}
.modal {
  background: #faf8f3;
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 90%;
  max-width: 640px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  position: relative;
  z-index: 1001;
}
.modal-lg { max-width: 780px; }
.modal h3 { margin: 0 0 16px 0; }
.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 16px; }
.form-grid .form-input { max-width: none; }

/* 响应式 */
@media (max-width: 1000px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
