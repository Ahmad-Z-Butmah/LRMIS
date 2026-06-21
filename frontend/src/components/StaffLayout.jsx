import React from 'react'
import Layout from './Layout'
import StaffNavBar from './StaffNavBar'

export default function StaffLayout({ children }) {
  return (
    <Layout>
      <StaffNavBar />
      {children}
    </Layout>
  )
}
