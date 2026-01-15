'use client'

import { useState } from 'react'
import { Settings, Building2, Key, Bell, Globe, Save, Eye, EyeOff } from 'lucide-react'

interface CompanyConfig {
  company_name: string
  company_intro: string
  contact_phone: string
  contact_email: string
  contact_wechat: string
  address: string
  advantages: string[]
}

interface ApiConfig {
  keling_access_key: string
  keling_secret_key: string
  dashscope_api_key: string
  serper_api_key: string
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'company' | 'api' | 'notification' | 'system'>('company')
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})
  const [isSaving, setIsSaving] = useState(false)

  const [companyConfig, setCompanyConfig] = useState<CompanyConfig>({
    company_name: '',
    company_intro: '',
    contact_phone: '',
    contact_email: '',
    contact_wechat: '',
    address: '',
    advantages: ['专业服务', '时效保证', '价格透明']
  })

  const [apiConfig, setApiConfig] = useState<ApiConfig>({
    keling_access_key: '',
    keling_secret_key: '',
    dashscope_api_key: '',
    serper_api_key: ''
  })

  const [notificationConfig, setNotificationConfig] = useState({
    high_intent_threshold: 60,
    enable_wechat_notify: true,
    enable_email_notify: false,
    quiet_hours_start: '22:00',
    quiet_hours_end: '08:00'
  })

  const toggleSecretVisibility = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 1000))
    setIsSaving(false)
    alert('设置已保存！')
  }

  const tabs = [
    { id: 'company', label: '公司信息', icon: Building2 },
    { id: 'api', label: 'API配置', icon: Key },
    { id: 'notification', label: '通知设置', icon: Bell },
    { id: 'system', label: '系统设置', icon: Globe }
  ]

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="w-7 h-7 text-cyber-blue" />
            系统设置
          </h1>
          <p className="text-gray-400 mt-1">管理系统配置、API密钥和通知设置</p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {isSaving ? '保存中...' : '保存设置'}
        </button>
      </div>

      {/* 标签页 */}
      <div className="flex gap-2 bg-dark-purple/40 rounded-xl p-1.5">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-cyber-blue text-white'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 公司信息 */}
      {activeTab === 'company' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4">公司基本信息</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">公司名称</label>
              <input
                type="text"
                value={companyConfig.company_name}
                onChange={e => setCompanyConfig(prev => ({ ...prev, company_name: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入公司名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">联系电话</label>
              <input
                type="text"
                value={companyConfig.contact_phone}
                onChange={e => setCompanyConfig(prev => ({ ...prev, contact_phone: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入联系电话"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">联系邮箱</label>
              <input
                type="email"
                value={companyConfig.contact_email}
                onChange={e => setCompanyConfig(prev => ({ ...prev, contact_email: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入联系邮箱"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">微信号</label>
              <input
                type="text"
                value={companyConfig.contact_wechat}
                onChange={e => setCompanyConfig(prev => ({ ...prev, contact_wechat: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入微信号"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">公司地址</label>
            <input
              type="text"
              value={companyConfig.address}
              onChange={e => setCompanyConfig(prev => ({ ...prev, address: e.target.value }))}
              className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              placeholder="请输入公司地址"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">公司简介</label>
            <textarea
              value={companyConfig.company_intro}
              onChange={e => setCompanyConfig(prev => ({ ...prev, company_intro: e.target.value }))}
              rows={4}
              className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none resize-none"
              placeholder="请输入公司简介，这将用于AI员工在与客户沟通时介绍公司"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">公司优势</label>
            <div className="flex flex-wrap gap-2">
              {companyConfig.advantages.map((adv, index) => (
                <span
                  key={index}
                  className="px-3 py-1.5 bg-cyber-blue/20 text-cyber-blue rounded-full text-sm flex items-center gap-2"
                >
                  {adv}
                  <button
                    onClick={() => setCompanyConfig(prev => ({
                      ...prev,
                      advantages: prev.advantages.filter((_, i) => i !== index)
                    }))}
                    className="hover:text-white"
                  >
                    ×
                  </button>
                </span>
              ))}
              <input
                type="text"
                placeholder="添加优势..."
                className="px-3 py-1.5 bg-deep-space/50 border border-gray-700 rounded-full text-sm text-white focus:border-cyber-blue focus:outline-none w-32"
                onKeyDown={e => {
                  if (e.key === 'Enter' && e.currentTarget.value) {
                    setCompanyConfig(prev => ({
                      ...prev,
                      advantages: [...prev.advantages, e.currentTarget.value]
                    }))
                    e.currentTarget.value = ''
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* API配置 */}
      {activeTab === 'api' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4">API密钥配置</h2>
          <p className="text-gray-400 text-sm mb-6">
            请妥善保管您的API密钥，不要泄露给他人。密钥变更后需要重启服务生效。
          </p>

          {[
            { key: 'keling_access_key', label: '可灵AI Access Key', desc: '用于AI视频生成' },
            { key: 'keling_secret_key', label: '可灵AI Secret Key', desc: '用于AI视频生成' },
            { key: 'dashscope_api_key', label: '通义千问 API Key', desc: '用于AI对话和文案生成' },
            { key: 'serper_api_key', label: 'Serper API Key', desc: '用于线索搜索' }
          ].map(item => (
            <div key={item.key}>
              <label className="block text-sm font-medium text-gray-300 mb-1">{item.label}</label>
              <p className="text-gray-500 text-xs mb-2">{item.desc}</p>
              <div className="relative">
                <input
                  type={showSecrets[item.key] ? 'text' : 'password'}
                  value={(apiConfig as any)[item.key]}
                  onChange={e => setApiConfig(prev => ({ ...prev, [item.key]: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none pr-12"
                  placeholder={`请输入${item.label}`}
                />
                <button
                  type="button"
                  onClick={() => toggleSecretVisibility(item.key)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                >
                  {showSecrets[item.key] ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 通知设置 */}
      {activeTab === 'notification' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4">通知设置</h2>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              高意向客户通知阈值
            </label>
            <p className="text-gray-500 text-xs mb-2">
              当客户意向分数达到此阈值时，系统将发送通知提醒
            </p>
            <input
              type="number"
              value={notificationConfig.high_intent_threshold}
              onChange={e => setNotificationConfig(prev => ({ ...prev, high_intent_threshold: parseInt(e.target.value) }))}
              className="w-32 px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              min={0}
              max={100}
            />
            <span className="text-gray-400 ml-2">分</span>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-300">通知方式</h3>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={notificationConfig.enable_wechat_notify}
                onChange={e => setNotificationConfig(prev => ({ ...prev, enable_wechat_notify: e.target.checked }))}
                className="w-5 h-5 rounded bg-deep-space/50 border-gray-700 text-cyber-blue focus:ring-cyber-blue"
              />
              <span className="text-white">微信通知</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={notificationConfig.enable_email_notify}
                onChange={e => setNotificationConfig(prev => ({ ...prev, enable_email_notify: e.target.checked }))}
                className="w-5 h-5 rounded bg-deep-space/50 border-gray-700 text-cyber-blue focus:ring-cyber-blue"
              />
              <span className="text-white">邮件通知</span>
            </label>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-2">免打扰时段</h3>
            <div className="flex items-center gap-4">
              <input
                type="time"
                value={notificationConfig.quiet_hours_start}
                onChange={e => setNotificationConfig(prev => ({ ...prev, quiet_hours_start: e.target.value }))}
                className="px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              />
              <span className="text-gray-400">至</span>
              <input
                type="time"
                value={notificationConfig.quiet_hours_end}
                onChange={e => setNotificationConfig(prev => ({ ...prev, quiet_hours_end: e.target.value }))}
                className="px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              />
            </div>
          </div>
        </div>
      )}

      {/* 系统设置 */}
      {activeTab === 'system' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4">系统设置</h2>

          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-4">默认语言</h3>
            <select className="px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none">
              <option value="zh-CN">中文 (简体)</option>
              <option value="en-US">English (US)</option>
            </select>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-4">AI模型配置</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">主模型</label>
                <select className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none">
                  <option value="qwen-max">通义千问 Max</option>
                  <option value="qwen-plus">通义千问 Plus</option>
                  <option value="qwen-turbo">通义千问 Turbo</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">创造性参数</label>
                <input
                  type="number"
                  defaultValue={0.7}
                  step={0.1}
                  min={0}
                  max={1}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
