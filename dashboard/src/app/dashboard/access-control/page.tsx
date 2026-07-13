import { Metadata } from "next";
import AccessControlClient from "@/components/access-control/AccessControlClient";

export const metadata: Metadata = {
  title: "Identity & Access Management | VeriField Nexus",
  description: "Enterprise IAM module for user and role management.",
};

export default function AccessControlPage() {
  return <AccessControlClient />;
}
